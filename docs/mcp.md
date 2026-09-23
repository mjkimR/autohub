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

1. Sign in to the Hub as an administrator and open **Machine keys**
   (`/admin/machines`). Create a dedicated machine, for example `personal-mcp`,
   with the **MCP read** and **MCP write** scopes (`autohub:mcp:read`,
   `autohub:mcp:write`). A read-only connection needs only MCP read. Scopes apply
   to the whole installation; this first release does not provide project-specific ACLs.
2. Under the machine's **Keys**, issue a key with a label and optional expiry.
   The key is shown once with ready-to-copy Claude Code and Codex snippets; it is
   not retrievable later. The same operations are available through
   `POST /api/v1/machines` and `POST /api/v1/machines/{machine_id}/keys` in `/docs`.
   Existing machine management also accepts the deployment root credential, but MCP does not.
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
   For Claude Code, run the copied `claude mcp add --transport http ... --header
   "Authorization: Bearer <key>"` command in the project directory; it registers the
   server in local scope for that project only.
   Other Streamable HTTP clients can use the same URL with
   `Authorization: Bearer <issued-key>`; their live compatibility remains to be verified.

To rotate, issue a replacement on the same machine, switch the client, then
revoke the old key on the **Machine keys** page. Revoked/expired keys and
inactive machines fail on the next request. Scheduler-only keys, root keys,
GitHub tokens and user login tokens are not MCP credentials.

## First repository

- Find an existing project with `projects.get` using `repository` (`owner/repository`),
  or search with `projects.list`.
  For a new connection, inspect `connectors.list` and `catalogs.list`, then call
  `projects.create` with the repository, connector ID and existing CI verification
  contract. Connector credentials are created/rotated in the existing Hub UI.
  See [CI connection contract](ci-contract.md) and the
  [existing templates](../templates/github-actions/README.md).
- Use `projects.readiness` to see, per catalog, whether a test can start and which
  requirements are missing or need manual confirmation. This is a configuration check. `connection_tests.start` verifies the actual provider/CI
  integration and may create a temporary branch and PR. Generate its `request_id`
  once and reuse it if the response is lost. Observe status, evidence links (test PR,
  CI run, provider response) and cleanup with `connection_tests.get`; the existing
  maintenance scheduler advances the test. `connection_tests.list` shows a project's
  recent tests after a lost ID.
- Prepare an open PR through your normal Git/GitHub workflow, then call
  `runs.enroll`. Set `pull_request.implemented=true` for code already implemented;
  otherwise the selected catalog receives the implementation work. The project's
  existing automation and Draft/Ready policies still apply.
- Keep the run ID and PR link. Use `runs.get` for state and `runs.attempts` for
  outcomes, failure details and provider conversation links. Disconnecting the
  MCP client does not cancel work. `runs.get` and `connection_tests.get` accept
  `wait_seconds` (up to 20) to return on the next state change instead of polling.

## Public tools

| Scope | Tools |
| --- | --- |
| `autohub:mcp:read` | `projects.list`, `projects.get`, `projects.readiness`, `catalogs.list`, `connectors.list`, `runs.list`, `runs.get`, `runs.attempts`, `connection_tests.list`, `connection_tests.get` |
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

`projects.update` changes only the fields it receives (REST: `PATCH /api/v1/projects/{id}`):
nested objects merge, lists replace, and `github: null` disconnects. The merged
configuration is validated as a whole, and it requires the latest `expected_revision`.
Error codes follow the HTTP status (`NOT_FOUND`, `CONFLICT`, `INVALID_REQUEST`, ...),
and recoverable conflicts carry a `fix` hint. Duplicate repository
creation and active PR enrollment conflict; find the existing project/run after a
lost response (`runs.list` filters by exact `pull_number`). There is no universal mutation deduplication layer. After losing a
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
