---
id: DESIGN-credential-sealing
title: "Credential sealing for connectors and notification channels"
status: active
area: projects
summary: "Explains how Hub seals connector credentials and notification bot tokens with one AES-256-GCM key, the stored layout and associated data every later read must reproduce, and what a key change or re-encryption has to cover; secrecy guarantees stay with the owning capabilities."
related_capabilities: [CAP-PROJ-project-connections, CAP-NOTIFY-operator-notifications, CAP-CONN-connection-verification]
entrypoints:
  - modules/hub/app/features/configuration/connectors/crypto.py
  - modules/hub/app/features/configuration/connectors/services.py
  - modules/hub/app/features/notifications/services.py
---

# [DESIGN-credential-sealing] Credential sealing for connectors and notification channels

Two tables hold secrets that Hub must read back on later requests, ticks and maintenance passes: connector
credentials in `connectors` and Telegram bot tokens in `notification_channels`. Both use one cipher and one
configured key. A read succeeds only if it reproduces the exact associated data used at write time, and only the
current key version can decrypt. A key change or bulk re-encryption therefore has to cover every row in both tables,
and it also changes evidence derived from the stored bytes. The guarantees (encrypt at rest, never return secrets)
belong to `CAP-PROJ-project-connections` rules 5 and 6 and `CAP-NOTIFY-operator-notifications` rules 1 and 2.

## Sealing and reading

`ConnectorCredentialCipher` in
[crypto.py](../../../../modules/hub/app/features/configuration/connectors/crypto.py) seals a JSON object.

1. Serialize the object with orjson and sorted keys.
2. Draw a fresh random 12-byte nonce.
3. Encrypt with AES-256-GCM under the current key, with the associated data below.
4. Store the ciphertext (which includes the 16-byte authentication tag), the nonce and the current key-version
   label.

Decryption looks up the key for the stored version, authenticates with the same associated data and requires the
plaintext to be a JSON object. A tag mismatch raises `CredentialDecryptionError`, a `ValueError`.

Associated data is `connector:<owner-id>:<scope>:v1`, UTF-8 encoded:

| Owner | `<owner-id>` | `<scope>` | Writer |
| --- | --- | --- | --- |
| Connector | `connectors.id` | `connectors.provider`, for example `github` | `ConnectorService` create and credential patch in [services.py](../../../../modules/hub/app/features/configuration/connectors/services.py) |
| Notification channel | `notification_channels.id` | `notification:<kind>`, for example `notification:telegram` | `NotificationChannelService` create and token patch in [notifications/services.py](../../../../modules/hub/app/features/notifications/services.py) |

The scope keeps a bot token from authenticating as a connector credential, and binds each ciphertext to its row and
provider. Copying ciphertext to another row, or changing a connector's `provider`, makes decryption fail.

The key comes from `CONNECTOR_CREDENTIAL_KEY`, base64 that must decode to exactly 32 bytes, labelled by
`CONNECTOR_CREDENTIAL_KEY_VERSION` (default `"1"`). `EnvironmentCredentialKeyProvider` holds only that one key.
`get_key` raises `ValueError` for any other version label, so there is no period in which an old and a new key both
decrypt.

## Stored layout

The same three columns exist in `connectors` and in `notification_channels`:

| Column | Type | Content |
| --- | --- | --- |
| `credentials_ciphertext` | bytes | AES-GCM ciphertext followed by its 16-byte tag |
| `credentials_nonce` | bytes | 12-byte nonce, fresh for every seal |
| `credential_key_version` | string | Version label of the key used to seal the row |

Plaintext objects:

- Connector: the credential object supplied to the connector API; readers that need a token require a nonempty
  string `token`.
- Notification channel: `{"token": "<bot token>"}`, stripped of surrounding whitespace.

Example, with placeholder values only: a channel with ID `<channel-uuid>` and kind `telegram` stores
`credential_key_version = "1"`, a 12-byte nonce, and the encryption of `{"token":"<bot-token>"}` under associated
data `connector:<channel-uuid>:notification:telegram:v1`.

## Readers that depend on the stored bytes

- Connector token reads (`ReadConnectorTokenUseCase`), project dispatch and observation tasks, Jules session
  orchestration, shared maintenance and MCP dependencies decrypt connector rows.
- `NotificationChannelService.bot_token` decrypts channel rows for broadcasts, channel tests and decision-notice
  delivery. The decision worker treats a decryption failure as `missing-destination`.
- `describe_configuration` in
  [connection_tests/configuration.py](../../../../modules/hub/app/features/project_management/connection_tests/configuration.py)
  puts each required connector's `credential_key_version` and
  `credential_version = sha256(credentials_ciphertext + credentials_nonce)` into the connection-test configuration
  fingerprint.

A channel token patch compares the new token with the decrypted old one. Only a different token advances the
channel's destination generation, so resealing the same token does not disable a decision subscription.

## Key change and re-encryption

Because only the current version decrypts, changing the key means:

1. Decrypt every row of `connectors` and `notification_channels` with the old key, using each row's own associated
   data.
2. Reseal each plaintext with the new key, a fresh nonce and the new version label.
3. Serve the new key and label only after every row is resealed. A row left on the old label fails on its next read.

Resealing a connector row changes its ciphertext and nonce, and a new label changes `credential_key_version`. Either
change alters the connection-test fingerprint, so earlier successful tests read `configuration_current: false`
until a new test runs (`CAP-CONN-connection-verification` §4). The repository ships no re-encryption command; key
provisioning is described in the [hub README](../../../../modules/hub/README.md#connector-credential-encryption).

## Authority boundary

- `CAP-PROJ-project-connections` rules 5 and 6 own connector credential encryption and omission.
- `CAP-NOTIFY-operator-notifications` rules 1, 2 and 20 own channel token sealing, omission and destination
  rotation.
- `CAP-CONN-connection-verification` §4 owns what the configuration fingerprint covers and `configuration_current`.
- `ARCH-02-constraints` owns the rule that documentation and logs never expose connector credentials.

## Update triggers

- `ConnectorCredentialCipher`, `_aad`, `_sealing_scope` or `EnvironmentCredentialKeyProvider` change the
  algorithm, nonce size, associated data, serialization or the set of versions that decrypt.
- Another table starts storing values sealed by this cipher.
- `describe_configuration` changes how credential columns enter the fingerprint.
- Recheck with `just test modules/hub/tests/unit/features/configuration/connectors/test_crypto.py`.
