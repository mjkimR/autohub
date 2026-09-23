# AutoHub MCP

The existing Hub process serves a Streamable HTTP MCP endpoint at
`https://YOUR_HUB_HOST/mcp/`. `/mcp` redirects to this canonical URL. No local
server package, skill, plugin, or per-repository agent configuration is required.

Status: implemented with the published `app-common` commit
`e4b8d1dee7c2b79e0bcb4ac246802eafc13c77ca`, pinned in the Python and APM
manifests and locks. The full test suite, lint, type checks, UI build, and APM
audit pass with packages installed from this commit. This endpoint has not yet
been deployed or verified in a live Codex session.

## Connect once

1. Open the Hub's `/docs`, use **Authorize** to sign in as the human administrator,
   and create a dedicated machine with `POST /api/v1/machines`:

   ```json
   {"name": "personal-mcp", "scopes": ["autohub:mcp:read", "autohub:mcp:write"]}
   ```

   A read-only connection needs only `autohub:mcp:read`. Scopes apply to the whole
   installation; this first release does not provide project-specific ACLs.
2. Issue a key using `POST /api/v1/machines/{machine_id}/keys`, with a label and
   optional `expires_at`. Save the returned `key` once; it is not retrievable later.
   Keep the machine ID and key ID for rotation and revocation. Existing machine
   management also accepts the deployment root credential, but MCP does not.
3. Make the key available as `AUTOHUB_MCP_KEY` in the environment of the client
   process, then add this to your **user** `~/.codex/config.toml`:

   ```toml
   [mcp_servers.autohub]
   url = "https://YOUR_HUB_HOST/mcp/"
   bearer_token_env_var = "AUTOHUB_MCP_KEY"
   ```

   Restart the client after changing its environment/configuration. The variable
   value is the issued key, without a `Bearer ` prefix. This uses the documented
   [Codex HTTP MCP settings](https://developers.openai.com/codex/mcp#configure-with-configtoml).
   No `codex mcp login` is needed: this endpoint uses manual bearer authentication,
   not an OAuth discovery/login flow.
4. Confirm the server appears in `/mcp` and ask it to list AutoHub projects.
   Other Streamable HTTP clients can use the same URL with
   `Authorization: Bearer <issued-key>`; their live compatibility remains to be verified.

To rotate, issue a replacement on the same machine, switch the client, then
`DELETE /api/v1/machines/{machine_id}/keys/{old_key_id}`. Revoked/expired keys and
inactive machines fail on the next request. Scheduler-only keys, root keys,
GitHub tokens and user login tokens are not MCP credentials.

## First repository

- Find an existing project with `projects.list` using `owner/repository`.
  For a new connection, inspect `connectors.list` and `catalogs.list`, then call
  `projects.create` with the repository, connector ID and existing CI verification
  contract. Connector credentials are created/rotated in the existing Hub UI.
  See [CI connection contract](ci-contract.md) and the
  [existing templates](../templates/github-actions/README.md).
- Use `projects.readiness` to inspect configured provider requirements. This is a
  configuration check. `connection_tests.start` verifies the actual provider/CI
  integration and may create a temporary branch and PR. Generate its `request_id`
  once and reuse it if the response is lost. Observe status and cleanup with
  `connection_tests.get`; the existing maintenance scheduler advances the test.
- Prepare an open PR through your normal Git/GitHub workflow, then call
  `runs.enroll`. Set `pull_request.implemented=true` for code already implemented;
  otherwise the selected catalog receives the implementation work. The project's
  existing automation and Draft/Ready policies still apply.
- Keep the run ID and PR link. Use `runs.get` for state and `runs.attempts` for
  outcomes, failure details and provider conversation links. Disconnecting the
  MCP client does not cancel work. Poll only when needed.

## Public tools

| Scope | Tools |
| --- | --- |
| `autohub:mcp:read` | `projects.list`, `projects.get`, `projects.readiness`, `catalogs.list`, `connectors.list`, `runs.list`, `runs.get`, `runs.attempts`, `connection_tests.get` |
| `autohub:mcp:write` | `projects.create`, `projects.update`, `runs.enroll`, `runs.pause`, `runs.resume`, `runs.cancel`, `connection_tests.start`, `connection_tests.cancel` |

Discovery exposes this fixed public list; calls enforce the matching scope.
Grant both scopes for a normal interactive connection. Internal leases, worker
callbacks, credential operations, deletion, recurring schedules, WorkPlans and
standalone session/report operations are not exposed in this first set.

List inputs bound page size to 100. Attempt history applies offset/limit in the
database and aggregates totals across the full run. Run and attempt outputs omit PR bodies, linked
issue bodies, request snapshots and lease tokens. Tools return structured
`{ok, result, error}` content. Failures set MCP `isError` and include the shared
application error/advisory. Tool annotations describe effects but do not authorize them.

`projects.update` requires the latest `expected_revision`. Duplicate repository
creation and active PR enrollment conflict; find the existing project/run after a
lost response. There is no universal mutation deduplication layer. After losing a
pause/resume/cancel response, read status before retrying. Connection test request
IDs use the existing durable deduplication. Cancellation does not promise to stop
already delivered provider work; follow cleanup status for connection tests.

## Runtime and verification

MCP uses stateless HTTP and JSON responses, sharing Hub startup/shutdown and the
existing database/scheduler. Authentication runs before initialization, discovery
and calls. Authentication's database transaction closes before a tool starts.
Browser Origin headers must match the endpoint host. The MCP routes precede the
SPA catch-all; REST authorization remains separate.

Run `just test tests/integration/mcp tests/integration/test_main.py tests/integration/auth`
for HTTP handshake/discovery, scope isolation, credential lifecycle, SPA routing,
project revisions, duplicate PR enrollment, run controls and connection-test retry
coverage. GitHub is mocked; these tests do not create remote branches or PRs.
Use `just lint`, `just check` and `just test` for the normal repository checks.
