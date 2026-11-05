# Access and client connections

Use this guide to configure operator accounts, managed MCP credentials and Google
login on a serving Hub. `CAP-ACCESS-authentication-authorization` owns account and
credential boundaries; `CAP-MCP-tool-access` owns endpoint/tool contracts. These
steps do not establish deployment or live-provider verification by themselves.

## MCP connections

Hub serves work tools at `https://YOUR_HUB_HOST/mcp/` and operations tools at
`https://YOUR_HUB_HOST/ops/mcp/`. Both endpoints run in the Hub process. No local
server package or per-repository plugin is required.

Keep the work connection as the normal inspection/execution connection. Add an
operations connection when configuring projects or running connection tests.
Use separate machines for their credentials: scopes belong to a machine, so a
second key on the same machine does not isolate its permissions.

| Connection | Suggested machine | Scopes | Client server name | Raw-key environment variable |
| --- | --- | --- | --- | --- |
| Work | `personal-mcp` | `autohub:mcp:read`, optionally `autohub:mcp:write` | `autohub` | `AUTOHUB_MCP_KEY` |
| Operations | `personal-mcp-ops` | `autohub:mcp:ops` | `autohub-ops` | `AUTOHUB_OPS_MCP_KEY` |

1. Sign in as a superadmin and open **Machine keys** (`/admin/machines`). Create
   the machine with its intended scopes. Read-only observation needs only MCP read.
2. Under that machine's **Keys**, issue a key with a label and optional expiry.
   Store the displayed key now; it is shown once. The issued-key notice supplies
   endpoint-specific client snippets.
3. Configure the client using the matching endpoint and bearer key. The
   environment-variable value is the raw issued key without a `Bearer ` prefix.
4. Refresh client discovery and call `projects_list` through the work connection.
   Use the operations connection for `projects_create`, `projects_update`,
   `connection_tests_start` and `connection_tests_cancel`.

The same administration operations are exposed through `POST /api/v1/machines`
and `POST /api/v1/machines/{machine_id}/keys`. Root administration credentials are
accepted there, not as MCP credentials. User login tokens, GitHub tokens and
dispatcher-only keys are also unsuitable for MCP.

### Client setup

The following snippets match the host's issued-key UI. Replace the host and key
placeholder locally; do not commit an issued key in repository configuration.

For Codex, make the raw key available in the client process environment, then
use `.codex/config.toml` for project configuration or `~/.codex/config.toml` for
user configuration:

```toml
[mcp_servers.autohub]
url = "https://YOUR_HUB_HOST/mcp/"
bearer_token_env_var = "AUTOHUB_MCP_KEY"

[mcp_servers.autohub-ops]
url = "https://YOUR_HUB_HOST/ops/mcp/"
bearer_token_env_var = "AUTOHUB_OPS_MCP_KEY"
```

Restart the client after changing its process environment or configuration. Hub
uses manually supplied machine bearer credentials; its MCP endpoints do not
provide an OAuth discovery/login flow.

For Antigravity, the issued-key UI supplies the following shape for
`.agents/mcp_config.json` or `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "autohub": {
      "serverUrl": "https://YOUR_HUB_HOST/mcp/",
      "headers": {"Authorization": "Bearer <issued-work-key>"}
    },
    "autohub-ops": {
      "serverUrl": "https://YOUR_HUB_HOST/ops/mcp/",
      "headers": {"Authorization": "Bearer <issued-operations-key>"}
    }
  }
}
```

For Claude Code, run the matching command in the project directory. Add
`--scope user` for user-wide configuration:

```bash
claude mcp add --transport http autohub https://YOUR_HUB_HOST/mcp/ --header "Authorization: Bearer <issued-work-key>"
claude mcp add --transport http autohub-ops https://YOUR_HUB_HOST/ops/mcp/ --header "Authorization: Bearer <issued-operations-key>"
```

Other Streamable HTTP clients use the same endpoints and bearer-header boundary.
Tool inventory and typed arguments come from discovery and `CAP-MCP-tool-access`.

### Rotation and connection recovery

Issue a replacement key on the same intended machine, switch the client and
confirm discovery, then revoke the previous key. Revoked/expired keys and disabled
machines fail on the next request. A valid key with the wrong endpoint scope
returns HTTP `403`; a missing/invalid key returns HTTP `401`.

Keep request IDs when invoking operations with durable replay identities. After
uncertain enrollment, find the Run by project and PR number before retrying.
After an uncertain pause/cancel, read current state. Read-only readiness checks
do not prove live provider access; explicitly start a connection test when that
evidence is needed. Client disconnection does not cancel provider work or cleanup.

## Google login

Keep the deployment's `FIRST_USER_EMAIL`/password recovery account available.
Google login is optional; enabling it does not bypass Hub account approval.
Approved accounts can operate all projects, so approve only intended operators.

1. Apply the matching application migration head before serving the updated image.
   The auth schema includes migration `b6f7a8b9c0d1`; an existing installation must
   apply later migrations too. Retire incompatible old workers before enabling
   the updated authentication flow.
2. Create a Google OAuth **Web application** client and register this callback:

   ```text
   https://YOUR_HUB_ORIGIN/api/v1/auth/google/callback
   ```

3. Store the client secret in the deployment secret store and configure the backend:

   ```text
   GOOGLE_AUTH_ENABLED=true
   GOOGLE_AUTH_CLIENT_ID=<client-id>
   GOOGLE_AUTH_CLIENT_SECRET=<secret>
   GOOGLE_AUTH_REDIRECT_URI=https://YOUR_HUB_ORIGIN/api/v1/auth/google/callback
   GOOGLE_AUTH_FRONTEND_URL=https://YOUR_HUB_ORIGIN/
   GOOGLE_AUTH_COOKIE_SECURE=true
   ```

4. Keep callback and frontend on the same origin. The default response mode is
   `query`; `GOOGLE_AUTH_RESPONSE_MODE=form_post` selects the POST callback and
   requires HTTPS with secure cookies. The client requests `openid email profile`.
5. Confirm callback-query logging controls before the live validation below.

The host strips the Google callback query from Uvicorn access logs. Cloud Run's
platform request log is separate and can retain the original request URL. Exclude
the matching callback request entries from retained platform logs; application
log filtering alone does not cover that surface. Retain neither authorization
codes nor client secrets in logs. Use the deployment's logging configuration and
[deployment procedure](cloud-run-deployment.md) for the serving environment.

### Account administration

Use **Account approval** (`/admin/users`) as a superadmin to inspect pending
accounts and choose approve/reject, suspend/activate or promote/demote. Review the
account version and optional reason before submitting an action; reload after a
conflict. The view displays the latest 50 access changes for the selected account.

Google identity does not automatically link an existing local account by email.
If Google reports an existing-account result, use that account's password login.
Do not use Google's Testing app mode as Hub's access gate. Account activation
requires a fresh login; it does not restore sessions invalidated by prior changes.

## Live validation

Perform these checks after a changed deployment and record its revision and scope:

1. Confirm the local recovery superadmin can still sign in by password.
2. Sign in through Google with an email distinct from existing local accounts;
   confirm pending approval grants no Hub session/access.
3. Approve the account from a separate administrator session; sign in again and
   confirm intended Hub access.
4. Suspend it; confirm protected API calls and refresh fail. Activate it; confirm
   old tokens remain invalid and a fresh Google sign-in succeeds.
5. Confirm a regular account cannot administer users, and protected changes to
   the acting administrator/bootstrap account are refused.
6. Exercise callback cancellation/failure and inspect retained application/platform
   logs without copying credential values. Check both `query` and `form_post` if
   the deployment intends to support both configurations.

The [recorded production evidence](../materials/2026-10/20261002-production-verification/report.md#google-authentication)
covers earlier real-account checks. It does not verify the current deployment.
Synthetic Google tokens and isolated database tests do not establish live login.

## Authentication rollback

To disable Google login, use `GOOGLE_AUTH_ENABLED=false`; do not downgrade its
schema merely to remove the button. Before rolling back authentication code,
disable external login and retire incompatible workers. The auth migration's
downgrade deactivates unapproved/version-revoked users and removes external
identities and approval/audit/flow data. Restore a backup if that history must be
preserved, and rotate the signing key before resuming an older authentication
implementation. Match application and schema versions for the selected rollback.
