# Google login and account approval

Implementation consumes published app-common commit `ca4e6a4fdca035314c4e032ca9397e633830ecf5` through pinned Git dependencies. Python and APM locks are updated; no sibling checkout links are required. Production deployment and live Google login verification are still pending.

## Behavior

- Existing email/password login remains available. The deployment's `FIRST_USER_EMAIL` account is the recovery superadmin.
- Google login is optional and disabled by default. New Google users always require administrator approval in AutoHub. There is no whitelist.
- Google verification proves identity; it does not grant Hub access or administrator rights. Google accounts use issuer + stable subject, never automatic email-based linking. If a Google email matches a local account, use the existing password login. Explicit identity linking is a separate future feature.
- `/admin/users` is available to superadmins. It supports approve/reject, suspend/activate, promote/demote, reason entry and the latest 50 audit events. The backend enforces the same authorization.
- Access changes revoke existing sessions. Reactivating an account does not revive its old tokens. The actor and bootstrap account cannot be suspended/rejected/demoted through the approval API; administrator deletion and bootstrap email changes are protected.
- Approval grants the existing operator access to **all Hub projects and configuration**. Per-repository membership/roles are not implemented. Approve only accounts intended to operate this personal Hub.
- Google login does not implement the OAuth authorization server needed for remote MCP clients. Machine scheduler credentials continue to use the existing API-key flow.

## Package composition and dependency pin

`app-prebuilt-auth` provides all authentication capabilities in one distribution. Its `user`, `google`, and `api_key` modules share the account model, approval rules and application sessions. Google remains disabled unless configured; no installation extras are needed.

AutoHub mounts `create_auth_router()` in its existing `/api/v1` router and retains its approval-required policy, bootstrap lifespan, human machine-key administrator dependency and scheduler scopes. The package registers all six auth tables by default. Existing migration `b6f7a8b9c0d1` supplies the complete schema; consolidation changes no table or column definitions and needs no additional migration.

The unified auth package and supporting Python app-common sources use the published commit above. `apm.yml`, its lock and deployed guide copies use the same commit. Old auth distributions and import namespaces are removed from this consumer. The unchanged frontend ESLint package retains its existing pin.

Reproduce with `uv sync --no-active --frozen` and `just skills`. Future updates must migrate the host schema as needed and update the related Python/APM pins together.

## Configure and deploy

Apply migration `b6f7a8b9c0d1` before starting the new backend. Existing users become approved with session version 0. Retire every old worker before enabling Google login.

Create a Google OAuth **Web application** client. Register exactly:

```text
https://YOUR_HUB_ORIGIN/api/v1/auth/google/callback
```

Use the deployment secret store for the client secret. Configure the backend:

```text
GOOGLE_AUTH_ENABLED=true
GOOGLE_AUTH_CLIENT_ID=<client-id>
GOOGLE_AUTH_CLIENT_SECRET=<secret>
GOOGLE_AUTH_REDIRECT_URI=https://YOUR_HUB_ORIGIN/api/v1/auth/google/callback
GOOGLE_AUTH_FRONTEND_URL=https://YOUR_HUB_ORIGIN/
GOOGLE_AUTH_COOKIE_SECURE=true
```

AutoHub forces external registration approval independently of the shared package's default. Keep the existing bootstrap credentials/signing key configuration. Callback and frontend must share the same origin. Do not rely on Google's Testing app mode as the Hub access gate.

For local development, use the Vite `/api` proxy: both URLs use `http://localhost:5173`, the callback keeps `/api/v1/auth/google/callback`, and `GOOGLE_AUTH_COOKIE_SECURE=false`. The client requests only `openid email profile`; no Drive/Gmail permissions are needed.

Configure application and proxy access logs to omit/redact callback query strings before enabling login. Authorization codes must not be retained in logs. Application tokens are never placed in URLs.

## Local verification (2026-09-22)

- app-common: full SQLite suite passed (1,074 tests); unified auth PostgreSQL suite passed (69 tests), including concurrent callback consumption and competing administrator changes.
- AutoHub: full backend suite passed (717 tests); frontend suite passed (124 tests). Auth/migration PostgreSQL coverage passed (22 tests). All suites were rerun after adopting the published unified auth package.
- Repeated verification against published Git dependencies passed: lint, Python/Svelte checks, frontend build, generated API types, full backend/UI tests and PostgreSQL auth/migration tests. The unified auth dependency and shared HTTP client are declared. The architecture checker reports three advisory warnings for existing isolated HTTP clients in Telegram, GitHub and Jules; these are outside the Google login implementation. APM audit passed all 10 checks.
- Temporary links were removed before installing the published dependencies. The checked-in locks now reproduce the implementation without local source links.

## Live validation

1. Confirm local superadmin password login still works.
2. Sign in with a Google email different from any existing local account: verify approval pending and no access/refresh token.
3. In a separate browser session, approve it at `/admin/users`; sign in again with Google and verify Hub access.
4. Suspend it; verify both API calls and token refresh fail. Activate it; old tokens must remain invalid, and a fresh Google login must succeed.
5. Verify a regular Google user cannot list/manage accounts. Verify the bootstrap account cannot be disabled or demoted.
6. Check callback cancellation/failure messages and confirm no credential values are recorded in access logs.

Automated tests use synthetic signed Google ID tokens and isolated SQLite/PostgreSQL databases. Google Console credentials, live Google browser consent, production migrations and Cloud Run rollout have not been performed.

## Rollback

Disable Google login and retire new workers before rolling code back. The migration downgrade deactivates pending/rejected and version-revoked users before removing approval/version columns; it also removes external identities and their audit/flow tables. This is destructive and loses approval/link history. Restore from backup to preserve that history, and rotate the signing key before resuming old authentication code. Do not downgrade merely to disable Google login; use `GOOGLE_AUTH_ENABLED=false` instead.
