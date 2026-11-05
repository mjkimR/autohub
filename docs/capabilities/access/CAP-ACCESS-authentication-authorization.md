---
id: CAP-ACCESS-authentication-authorization
title: Hub authentication and authorization
summary: "Human sessions and managed machine credentials authorize distinct Hub surfaces. This contract covers host wiring and session boundaries, while app-common owns the underlying identity and key implementations."
area: access
status: active
usecases:
  - UC-access-hub
  - UC-connect-hub-tools
entrypoints:
  - modules/hub/app/auth.py
  - modules/hub/app/auth_settings.py
  - modules/hub/app/main.py
---

# [CAP-ACCESS-authentication-authorization] Hub authentication and authorization

## 1. Summary

Auto Hub separates signed-in people, scoped machine credentials and machine-key
administration. The host mounts app-common authentication and makes external
registration approval mandatory. Credential possession does not grant access to
every transport or operation.

## 2. Scope & Boundary

- **In-Scope**: protected REST routing, host approval policy, browser-session
  integration, scheduler admission, machine-key administration and login caller
  identification.
- **Out-of-Scope**: identity/token/key cryptography and Google callback internals
  belong to `app-prebuilt-auth`; provider credentials belong to connector storage;
  MCP endpoint/tool scope enforcement belongs to `CAP-MCP-tool-access`; task-flow
  operation scopes belong to the SDK execution contract.

## 3. Business Rules & Policies

1. **Human REST access**: WHEN a caller requests a protected Hub REST operation,
   Hub MUST require a valid access token for a currently active, approved user.
   Checks: `modules/hub/tests/integration/auth/test_auth_api.py`.
2. **Credential roles**: IF a refresh token, root key or MCP-only machine key is
   supplied to a protected human REST operation, THEN Hub MUST refuse human access.
   Checks: `modules/hub/tests/integration/auth/test_auth_api.py`.
3. **External registration approval**: Hub MUST override the shared registration
   setting to require approval for external accounts.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
4. **Google availability**: WHERE Google authentication is disabled, Hub MUST
   report `enabled: false` through its options route.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
5. **Browser refresh isolation**: WHEN browser login succeeds, Hub MUST deliver
   its refresh credential through the `autohub_refresh` cookie rather than the
   login response body.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
6. **Browser logout**: WHEN browser logout succeeds, Hub MUST make that browser
   session's refresh credential unusable.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
7. **Frontend credential lifetime**: The UI MUST retain access tokens only in
   memory.
   Checks: `modules/hub-ui/src/lib/stores/session.test.ts`,
   `modules/hub-ui/src/lib/api/client.test.ts`.
8. **Dispatcher admission**: WHEN dispatch is triggered, Hub MUST require either
   an active signed-in user or a managed machine key with `autohub:dispatch`.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
9. **Machine administration**: WHEN machine credentials are administered, Hub
   MUST require the root administration credential or a signed-in superadmin.
   Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
10. **Key revocation**: WHEN a scheduler key is revoked, Hub MUST reject its next
    dispatch request with HTTP `401`.
    Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
11. **Login caller boundary**: WHEN Cloud Run supplies `X-Forwarded-For`, Hub MUST
    identify the caller from the last nonempty entry rather than an earlier
    client-supplied value.
    Checks: `modules/hub/tests/unit/common/test_auth_throttle.py`,
    `modules/hub/tests/integration/auth/test_auth_api.py`.
12. **Lockout notification**: WHEN repeated failed logins lock a caller out, Hub
    MUST mask the caller address in the operator notification.
    Checks: `modules/hub/tests/unit/common/test_auth_throttle.py`,
    `modules/hub/tests/integration/auth/test_auth_api.py`.
13. **Disabled Google start**: WHERE Google authentication is disabled, Hub MUST
    refuse its start route with HTTP `404`.
    Check: `modules/hub/tests/integration/auth/test_auth_api.py`.
14. **Obsolete refresh isolation**: IF a refresh response belongs to an obsolete
    session generation, THEN the UI MUST reject that result.
    Checks: `modules/hub-ui/src/lib/stores/session.test.ts`,
    `modules/hub-ui/src/lib/api/client.test.ts`.
15. **Callback log boundary**: WHEN Uvicorn logs a Google callback request, Hub
    MUST remove its query string while retaining the callback path and status.
    Check: `modules/hub/tests/unit/test_access_logging.py`.

## 4. Interfaces & Data Contracts

| Surface | Contract |
| --- | --- |
| `POST /api/v1/users/login/` | Password form; returns access/refresh tokens for non-browser clients |
| `POST /api/v1/users/login/refresh` | JSON `refresh_token`; access tokens are not refresh credentials |
| `POST /api/v1/auth/browser/login` | Browser login; access token in response, refresh cookie named `autohub_refresh` |
| `POST /api/v1/auth/browser/refresh` | Browser session renewal using its cookie |
| `POST /api/v1/auth/browser/logout` | Successful revocation returns HTTP `204` |
| `GET /api/v1/auth/google/options` | Whether Google login is enabled |
| `GET /api/v1/auth/google/start` | Starts the optional external login flow |
| `GET` or `POST /api/v1/auth/google/callback` | Uses GET in `query` mode or POST in `form_post` mode; the other method returns HTTP `405` with `Allow` |
| `POST /api/v1/auth/google/exchange` | Exchanges the short-lived callback cookie for account status and permitted session credentials; requires the configured frontend Origin |
| `POST /api/v1/dispatchers/trigger` | Human bearer token or machine `X-API-Key` with `autohub:dispatch` |
| `/api/v1/machines` and `/{machine_id}/keys` | Administration through `X-Root-API-Key` or superadmin bearer token |
| `GET /api/v1/users/me` | Current human account |
| `GET /api/v1/users/admin/` | Superadmin account listing |
| `POST /api/v1/users/admin/{user_id}/access` | `action`, `expected_version >= 0`, optional reason up to 500 characters; returns the account |
| `GET /api/v1/users/admin/{user_id}/access-events` | Latest 50 access events for that account |

The root credential is an administration credential, not an MCP or dispatch
credential. A valid machine lacking the dispatch scope receives HTTP `403` at the
trigger; missing or invalid credentials receive HTTP `401`. The integration
fixture's login-lockout configuration returns HTTP `429` and a `Retry-After`
header after its configured failed-login threshold; app-common owns the threshold
and lockout implementation.

### Shared identity and account administration

Hub mounts the pinned `app-prebuilt-auth` account and Google interfaces. Google
identity uses issuer `https://accounts.google.com` and the stable subject; matching
an existing email does not automatically link or grant that account's privileges.
A new external account remains pending until approval. Exchange results distinguish
`approved`, `pending`, `rejected` and `suspended`; nonapproved accounts receive no
session credentials. Google login is not an OAuth authorization server for MCP.

Account access actions are `approve`, `reject`, `suspend`, `activate`, `promote`
and `demote`. The shared service checks an active approved superadmin actor and
the account's `expected_version`; stale versions conflict. Accepted changes advance
`auth_version` and record actor/action/reason evidence, preventing reactivation
from reviving old session credentials. Reduction of the acting administrator's
access, the bootstrap account's access or the last active approved administrator's
access is refused. Activation and promotion require an approved account.

These shared-package behaviors were source-inspected in the pinned dependency's
Google and user access services. Host integration tests establish mandatory
approval and pending/inactive-account denial; the complete callback and
administrator transition matrix is not independently exercised by those host tests.
`modules/hub-ui/src/lib/features/auth/admin/UsersAdminView.integration.test.ts`
checks the reviewed action, version and reason submitted by the host UI.

Human access and machine scopes apply to the installation, not individual
repository memberships. The host has no per-project account ACL. Scopes belong
to machines, so issuing another key for the same machine does not create a
different scope boundary. Issuance displays the key once; the host's
`modules/hub-ui/src/lib/features/auth/machines/IssuedKeyNotice.svelte` provides
endpoint-specific snippets. The mounted shared API owns key storage/retrieval.

## 5. Implementation and verification

Source inspected: `modules/hub/app/auth.py`, `modules/hub/app/auth_settings.py`,
`modules/hub/app/main.py`, `modules/hub/app/router.py`,
`modules/hub/app/common/auth_throttle.py`,
`modules/hub/app/access_logging.py`,
`modules/hub-ui/src/lib/api/client.ts` and
`modules/hub-ui/src/lib/stores/session.svelte.ts`. The test paths above were
inspected as contract evidence; this document does not assert that those tests or
real Google/provider access were executed during its authoring.

The shared dependency's source/ref is pinned in
[Hub's manifest](../../../modules/hub/pyproject.toml); generated host interfaces
remain in `modules/hub-ui/src/lib/api/generated/users.d.ts` and
`modules/hub-ui/src/lib/api/generated/google-authentication.d.ts`.
The [access operations guide](../../operations/access.md) owns machine/client
setup, Google configuration and repeatable live validation.
