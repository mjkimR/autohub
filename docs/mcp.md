# AutoHub MCP

The existing Hub process serves a Streamable HTTP MCP endpoint at
`https://YOUR_HUB_HOST/mcp/`. `/mcp` redirects to this canonical URL. No local
server package, skill, plugin, or per-repository agent configuration is required.

Status: the original single endpoint has been deployed. The work/operations split
below is implemented locally and still needs deployment. Both endpoints share the
Hub process, database and scheduler; neither starts a separate service.

- Work: `/mcp/`, 13 tools, existing `autohub:mcp:read` / `autohub:mcp:write` keys.
- Operations: `/ops/mcp/`, 4 additional tools, dedicated `autohub:mcp:ops` key.
- Work owns all 9 inspection tools and four run mutations. Operations adds only
  four project/connection-test mutations, with no duplicate tool names. Even a key with all scopes cannot call
  a tool through the wrong endpoint. Ops-only keys cannot enter the work endpoint.

Keep the work connection enabled as the base. Issue the operations key on
**a separate machine** and enable its connection alongside work for configuration
or connection testing. Operations relies on work for inspection; disabling
operations leaves everyday execution and all inspection available.
Scopes belong to machines: issuing another key on the same machine does not
isolate permissions. Operations does not grant machine/key administration, REST
access, scheduler dispatch, credential editing or internal worker callbacks.

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
   `Authorization: Bearer <issued-key>`.

To rotate, issue a replacement on the same machine, switch the client, then
revoke the old key on the **Machine keys** page. Revoked/expired keys and
inactive machines fail on the next request. Scheduler-only keys, root keys,
GitHub tokens and user login tokens are not MCP credentials.

## Operations connection and upgrade

Create a separate machine such as `personal-mcp-ops` with **MCP operations**
(`autohub:mcp:ops`) only. Its issued-key notice generates `/ops/mcp/` connection
snippets with server name `autohub-ops` and environment variable
`AUTOHUB_OPS_MCP_KEY`. Store the raw key in that variable in the client environment.
Keep operations scope on its separate machine. Enable or disable the operations
connection as an addition to work, without replacing the base connection.
A combined-scope machine is supported for deliberate use; its notice
shows both configurations and each endpoint retains its own tool inventory.

Existing work keys and URLs keep working after deployment, but `projects_create`,
`projects_update`, `connection_tests_start` and `connection_tests_cancel` move to
operations. Existing callers must use the new connection for those tools; there
is no compatibility alias granting old write keys operational access. Refresh the
client's discovered tool list after upgrade. No database migration is required.
`/ops/mcp` redirects to `/ops/mcp/`, just as `/mcp` redirects to `/mcp/`.

### Tool contract changes

All 17 public tool names use lowercase snake_case and at most 64 characters.
Registration rejects other characters or longer names to avoid relying on client
name rewriting. For example, `projects.options` becomes `projects_options`,
`runs.enroll` becomes `runs_enroll`, and `connection_tests.start` becomes
`connection_tests_start`. Dotted names are not retained as aliases.
Refresh tool discovery after deployment and update saved calls/allowlists.
`catalogs.list` and `connectors.list` are replaced by `projects_options`, returning
`catalogs` and optional `connectors` pages. Use `connectors_page={}` for onboarding.
MCP now requires `pull_request.implemented` for enrollment,
`expected_revision` for resume, and `github.automation.auto_merge` when creating
a connected project. REST input contracts retain their existing defaults.

## First repository

- On the work connection, find an existing project with `projects_get` using `repository` (`owner/repository`),
  or search with `projects_list`.
  For a new repository, call `projects_options` with `connectors_page={}` on the
  work connection, then call `projects_create` on the operations connection with
  the repository, connector ID, existing CI verification contract and an explicit
  `github.automation.auto_merge` choice. Connector credentials are created/rotated in the existing Hub UI.
  See [CI connection contract](ci-contract.md) and the
  [existing templates](../templates/github-actions/README.md).
- Use `projects_readiness` to see, per catalog, whether a test can start and which
  requirements are missing or need manual confirmation. This is a configuration check,
  not a mandatory test before each run. On the operations connection,
  `connection_tests_start` verifies the actual provider/CI integration and may create a temporary branch and PR. Generate its `request_id`
  once and reuse it if the response is lost. Observe status, evidence links (test PR,
  CI run, provider response) and cleanup with `connection_tests_get`; the existing
  maintenance scheduler advances the test. `connection_tests_list` shows a project's
  recent tests after a lost ID. Work can inspect existing results without starting a test.
- Prepare an open PR through your normal Git/GitHub workflow, then call
  `runs_enroll`. Set `pull_request.implemented=true` for code already implemented;
  set it to `false` to request implementation work. The field is required. The project's
  existing automation and Draft/Ready policies still apply.
- Keep the run ID and PR link. Use `runs_get` for state and `runs_attempts` for
  outcomes, failure details and provider conversation links. Disconnecting the
  MCP client does not cancel work. `runs_get` and `connection_tests_get` accept
  `wait_seconds` (up to 20) to return on the next state change instead of polling.

## Public tools

| Surface | Required scope | Tools |
| --- | --- | --- |
| Work only (inspection) | `autohub:mcp:read` | `projects_list`, `projects_get`, `projects_readiness`, `projects_options`, `runs_list`, `runs_get`, `runs_attempts`, `connection_tests_list`, `connection_tests_get` |
| Work only | `autohub:mcp:write` | `runs_enroll`, `runs_pause`, `runs_resume`, `runs_cancel` |
| Operations only | `autohub:mcp:ops` | `projects_create`, `projects_update`, `connection_tests_start`, `connection_tests_cancel` |

Discovery exposes each endpoint's fixed list; calls enforce the matching scope.
Grant read and write for a normal work connection, or read only for observation.
The operations scope covers only its four mutations. Read configuration, revisions,
readiness, test evidence and cleanup status through the work connection.
Internal leases, worker callbacks, credential operations, deletion, recurring
schedules, WorkPlans and standalone session/report operations remain unexposed.
With both connections enabled, discovery contains 17 unique tools and no duplicates.
The [tool review](mcp-tool-review-2026-09-29.md) rates each unique tool and records
the completed consolidation and usage improvements.

List inputs bound page size to 100. Attempt history applies offset/limit in the
database and aggregates totals across the full run. Run and attempt outputs omit PR bodies, linked
issue bodies, request snapshots and lease tokens. Tools return structured
`{ok, result, error}` content. Failures set MCP `isError` and include the shared
application error/advisory. Tool annotations describe effects but do not authorize them.

`projects_update` changes only the fields it receives (REST: `PATCH /api/v1/projects/{id}`):
nested objects merge, lists replace, and `github: null` disconnects. The merged
configuration is validated as a whole, and it requires the latest `expected_revision`.
Error codes follow the HTTP status (`NOT_FOUND`, `CONFLICT`, `INVALID_REQUEST`, ...),
and recoverable conflicts carry a `fix` hint. Duplicate repository
creation and active PR enrollment conflict; find the existing project/run after a
lost response (`runs_list` filters by exact `pull_number`). There is no universal mutation deduplication layer. After losing a
pause/resume/cancel response, read status before retrying. Connection test request
IDs use the existing durable deduplication. Cancellation does not promise to stop
already delivered provider work; follow cleanup status for connection tests.

## Choosing options and interpreting readiness

`projects_options` returns catalog choices with public capacity/capability fields.
Use `capability="pipeline_delivery"` or `"connection_test"`, and optionally
`enabled_only=true`. `offset`/`limit` page catalogs **after** filtering. Provide
`project_id` to return its configured selection independently of the page/filter;
this selection is not a guarantee of current availability. With no project, the
selection fields are null. The default Codex key is reported even if a metadata-only
installation has not seeded its catalog row yet; options does not create it.

Connector choices are omitted unless `connectors_page` is supplied. Its independent
`offset`/`limit` apply to the connector page, with a separate total. Credentials
and connector configuration are never returned. Create/rotate credentials in the UI.

`projects_readiness` accepts optional `ai_catalog_id` and returns
`check_kind="configuration_only"`. Per-catalog `status` is `blocked`,
`manual_checks`, or `configured`; `ready=true` means the configuration permits a
test, **not** that manual requirements or actual provider/CI access were verified.
The `pending` entries describe missing/manual checks. It is not a per-run prerequisite.

## Mutation and recovery workflow

- `projects_create`: explicitly supply `github.automation.auto_merge` when connecting
  GitHub. Other automation defaults remain visible in the input schema and the
  effective settings are returned. A project without GitHub can still be created.
- `projects_update`: optionally set `dry_run=true` to validate the merged configuration,
  including connector/catalog validity and repository conflicts, without saving.
  The response includes `applied=false`, the proposed configuration at the current
  revision and `changes` with each path's before/after values. Apply the same patch
  and expected revision with `dry_run=false`; `applied=true` returns the new revision.
  A preview does not reserve anything. A concurrent edit still causes a conflict;
  re-read and reconsider the patch. No human approval or mandatory preview is added.
  Preview validates stored configuration, not live provider access.
- `runs_enroll`: `implemented` is required to distinguish CI observation from requesting
  implementation. After a lost response, use `runs_list` with both `project_id` and
  `pull_number` before retrying. Existing duplicate-enrollment conflict rules remain.
- `runs_resume`: inspect the paused/blocked run and its cause, then send its
  `expected_revision`. The comparison runs under the run lock before GitHub I/O;
  the existing second-phase revision check also rejects changes during reconciliation.
  If the response is lost, read the current state rather than blindly replaying.
- `connection_tests_start`: its `request_id` is also the resulting test ID. After a
  lost response, call `connection_tests_get` with that ID or replay the original
  request. Optional `expected_project_revision` rejects a new test if the project
  changed. An existing request ID replays before that check, preserving recovery.
  It does not pin catalog/connector changes; the existing start/worker checks still
  validate the configuration. One active test per project remains enforced.
- `connection_tests_list`: filter by `ai_catalog_id`, `status`, or
  `configuration_current`. Filters and pagination apply within the latest 30 entries;
  `history_limit=30` makes that boundary explicit. `total_count` is the matching count
  in that window; use `next_offset` with the same filters, or get an older known ID.
  Concurrent new tests can shift offset pages, so use IDs for stable tracking.
- Test responses include `next_action`: `wait`, `inspect_cleanup`, `inspect_failure`,
  `review_configuration`, or `done`. Cleanup failure takes precedence; a successful
  test with pending cleanup is still `wait`, and a stale successful test is not `done`.

## Runtime and verification

MCP uses stateless HTTP and JSON responses, sharing Hub startup/shutdown and the
existing database/scheduler. Authentication runs before initialization, discovery
and calls on each endpoint. Authentication's database transaction closes before a tool starts.
Browser Origin headers must match the endpoint host. The MCP routes precede the
SPA catch-all; REST authorization remains separate.

Run `just test tests/unit/mcp tests/integration/mcp tests/integration/test_main.py tests/integration/auth`
for HTTP handshake/discovery, cross-endpoint discovery and call isolation, credential lifecycle, REST bypass rejection, SPA routing,
project revisions, duplicate PR enrollment, run controls and connection-test retry
coverage. GitHub is mocked; these tests do not create remote branches or PRs.
Use `just lint`, `just check` and `just test` for the normal repository checks.
