# Auto Hub - Backend

This is the FastAPI backend for Auto Hub, built on the existing scheduler engine.

See the [Root README](../../README.md), [architecture](../../docs/architecture.md), and
[CI observation contract](../../docs/ci-contract.md) for current scope and development direction.

## Development

Run commands from the repository root using the [justfile](../../justfile).
See [development and operations](../../docs/development.md) for verification and scheduler behavior.

## Connector credential encryption

Connector credentials are encrypted with AES-256-GCM before they are stored in the database. The base64-encoded
32-byte key is supplied as `CONNECTOR_CREDENTIAL_KEY`, normally as one field in the application's `APP_SECRETS_JSON`
bundle. Generate it with `openssl rand -base64 32`. The `CONNECTOR_CREDENTIAL_KEY_VERSION` label remains stored with
each encrypted row for future re-encryption support; changing the key currently requires re-encrypting the stored
connector credentials before removing the old key.


## Shared PostgreSQL database

Set `DB_SCHEMA=autohub` to keep this application's tables and `alembic_version` in
its own schema of a shared database (for example, Supabase's `postgres` database).
Run `just db-upgrade` from the repository root before starting the application; Alembic
creates the schema automatically. The migration role needs database `CREATE`
privileges. Normal application connections do not create schemas.

An empty/unset `DB_SCHEMA` preserves the existing default-schema behavior, and
SQLite ignores this setting. This does not move existing `public` tables: migrate
existing data separately before enabling it. Schema names use lowercase letters,
digits, and underscores, start with a letter or underscore, and are at most 63
characters. Restart the process after changing the setting.

Runtime transactions select only the app schema plus the shared `extensions`
namespace using transaction-local search paths. Psycopg prepared statements are
disabled for schema-configured runtime engines, supporting Supavisor transaction
pooling. Use direct/session-pooler connections for migrations. Apps retain separate
migration histories; autogenerate inspects the selected default schema. Permissions
must also be granted per app role if access isolation is required.
