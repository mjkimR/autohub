---
id: CAP-MCP-tool-access
title: Scoped MCP tool access
summary: "Managed machine keys expose separate work and operations MCP tool surfaces. Transport authentication, tool scopes and typed business handlers constrain discovery and execution independently of human REST access."
area: mcp
status: active
usecases:
  - UC-connect-hub-tools
entrypoints:
  - modules/hub/app/mcp/server.py
  - modules/hub/app/mcp/auth.py
  - modules/hub/app/mcp/registration.py
---

# [CAP-MCP-tool-access] Scoped MCP tool access

## 1. Summary

Hub mounts a work MCP endpoint and an operations MCP endpoint with disjoint tool
registries. Each HTTP request authenticates its machine key before MCP processing;
each tool call additionally checks the operation's required scope.

## 2. Scope & Boundary

- **In-Scope**: endpoint admission, fixed tool discovery, read/write/operations
  scopes, typed tool input/output and delegation to Hub business operations.
- **Out-of-Scope**: machine credential provisioning belongs to
  `CAP-ACCESS-authentication-authorization`; execution and approval semantics belong
  to the owning PR, Work Plan, native SDD and connection capabilities; MCP clients
  own their connection UI and secret storage. OAuth client registration is not
  supplied by these endpoints.

## 3. Business Rules & Policies

1. **Machine transport authentication**: WHEN an MCP HTTP request arrives, Hub
   MUST require a valid managed machine key as `Authorization: Bearer <key>`.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
2. **Endpoint admission**: IF a valid key has no scope admitted by the selected
   endpoint, THEN Hub MUST refuse transport access with HTTP `403`.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
3. **Credential changes**: WHEN a key is revoked, expired or its machine is
   disabled, Hub MUST reject its next request with HTTP `401`.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
4. **Origin boundary**: IF a supplied Origin is not HTTP/HTTPS with the request's
   host, THEN Hub MUST refuse the MCP request with HTTP `403`.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
5. **Disjoint discovery**: Hub MUST expose work tools only at `/mcp/` and
   operations tools only at `/ops/mcp/`, including for keys holding every scope.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
6. **Per-tool authority**: IF a caller lacks a tool's required scope, THEN the
   registered tool MUST return an MCP error with `MCP_FORBIDDEN`.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
7. **Typed inputs**: IF tool input violates its declared schema, THEN Hub MUST
   return `MCP_INVALID_ARGUMENTS` with actionable validation details.
   Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
8. **Portable names**: WHEN a tool is registered, its name MUST be lowercase
   snake_case with at most 64 characters.
   Check: `modules/hub/tests/unit/mcp/test_registration.py`.
9. **Business-rule reuse**: WHEN a tool performs a mutation, Hub MUST retain the
   business operation's revision, idempotency and authorization checks.
   Checks: `modules/hub/tests/integration/mcp/test_mcp.py`,
   `modules/hub/tests/integration/mcp/test_work_decisions.py`.
10. **Bounded disclosure**: Hub MUST omit connector secrets, PR bodies and request
    snapshots from the inspected public option/run/attempt outputs.
    Check: `modules/hub/tests/integration/mcp/test_mcp.py`.
11. **REST separation**: A machine key carrying only MCP scopes MUST NOT authorize
    protected human REST operations through either bearer or `X-API-Key` headers.
    Check: `modules/hub/tests/integration/auth/test_auth_api.py`.

## 4. Interfaces & Data Contracts

| Surface | Admission scopes | Registered operations |
| --- | --- | --- |
| `/mcp/` | `autohub:mcp:read` or `autohub:mcp:write` | 13 read tools and 14 work mutations |
| `/ops/mcp/` | `autohub:mcp:ops` | Four operations mutations |

The transport uses stateless HTTP with JSON responses. Slashless endpoint paths
redirect with HTTP `307`. Missing/invalid machine credentials return HTTP `401`
with `WWW-Authenticate: Bearer realm="autohub-mcp"`. The root administration key,
human login tokens and dispatcher-only machine keys are not MCP credentials.

| Scope | Tools |
| --- | --- |
| Read | `projects_list`, `projects_get`, `projects_readiness`, `projects_options`, `runs_list`, `runs_get`, `runs_attempts`, `runs_questions`, `work_plans_list`, `work_plans_get`, `work_plans_activity`, `connection_tests_list`, `connection_tests_get` |
| Work write | `runs_enroll`, `runs_pause`, `runs_resume`, `runs_cancel`, `runs_ask`, `runs_answer`, `runs_dismiss_question`, `sdd_start_planning`, `sdd_start_development`, `work_plans_register`, `work_plans_update`, `work_plans_set_group`, `work_plans_control`, `work_plans_comment` |
| Operations | `projects_create`, `projects_update`, `connection_tests_start`, `connection_tests_cancel` |

Discovery returns the selected endpoint's fixed registry; read-only keys can
discover work mutations but cannot execute them. Tool results carry structured
`{ok, result, error}` content, and failed calls set MCP `isError`. Application
errors retain codes such as `NOT_FOUND`, `CONFLICT` and `INVALID_REQUEST`.
Ordinary page inputs allow `limit` 1–100 and nonnegative `offset`; connection-test
listing has the narrower window described below. Bounded waits allow
`wait_seconds` 0–20 where declared. Dotted names are not compatibility aliases.

### Project lookup, options and readiness

| Tool | MCP-specific input and result |
| --- | --- |
| `projects_list` | Optional `search` of up to 255 characters filters project name or repository; paged result includes `total_count` |
| `projects_get` | Exactly one of `project_id` or `repository`; repository lookup is case-insensitive |
| `projects_options` | Optional `capability` is `pipeline_delivery` or `connection_test`; `enabled_only` filters catalogs; optional `project_id` identifies its configured selection |
| `projects_readiness` | `project_id`, optional `ai_catalog_id`; returns `check_kind="configuration_only"`, per-catalog `ready`, `status` and pending requirements |

`projects_options` filters catalogs before applying catalog `offset`/`limit`.
Connector choices are omitted unless `connectors_page` is supplied; that nested
page has its own offset, limit and total. Connector views omit credentials and
connector configuration. Selection fields are independent of page/filter results:
`selected_catalog_id`, `selected_catalog_key`, and `selection_source` (`project`
or `default`). Without `project_id`, those fields are null. Reporting the default
Codex key does not create an unseeded catalog or establish capacity.

Readiness `status` is `blocked` when configuration cannot start a test,
`manual_checks` when the ready option still has manual prerequisites, or
`configured` otherwise. `pending` includes missing/manual requirements and omits
configured requirements. This operation contacts no provider and neither proves
CI/provider access nor introduces a required test before each run.

### Mutation wrappers and revision boundaries

The table specifies the MCP adapter shape. The owning domain capabilities define
business transitions and limits; MCP registration does not weaken them.

| Tool | Adapter contract |
| --- | --- |
| `projects_create` | Nested `project`; a connected project requires an explicit `project.github.automation.auto_merge` |
| `projects_update` | `project_id`, nested patch `project` with `expected_revision`, optional `dry_run=false` |
| `runs_enroll` | `project_id`, nested `pull_request`; `pull_request.implemented` is required, unlike the REST schema's default |
| `runs_resume` | `run_id` plus the domain resume fields, including stable `request_id` and current `expected_revision` |
| `work_plans_register` | `project_id`, nested `plan`; `plan.request_id` is required, although REST registration permits omission |
| `work_plans_get` | `project_id` and exactly one of `plan_id` or registration `request_id` |
| `work_plans_update` | `project_id`, `plan_id`, nested `plan` carrying the current `expected_revision` |
| `work_plans_control` | `project_id`, `plan_id`, nested `control` carrying `action` and `expected_revision` |
| `work_plans_set_group` | `project_id`, `plan_id`, nested `group` carrying `group_key`, `expected_revision` and optional reason |
| `work_plans_comment` | `project_id`, `plan_id`, nested `comment` carrying `request_id` and `body` |
| `work_plans_activity` | `project_id`, `plan_id`, ordinary page fields and optional `comments_only=false` |

A project preview validates the merged configuration and conflicts without
saving or reserving its revision. It returns `applied=false`, the proposed
configuration at the current revision, and `changes` containing `path`, `before`
and `after`. Applying the same patch/revision returns `applied=true` and the new
revision; a concurrent edit can still make that application conflict.

Work Plan actors are derived from the authenticated machine as
`machine:{machine_id}`; callers do not supply authoritative author names.
`work_plans_list` and `runs_list` share the domain `group_key` filter: omitted or
null selects all groups, empty selects ungrouped work, and a nonempty value matches
the exact trimmed key. The key is limited to 100 characters. Domain behavior
belongs to `CAP-WORK-work-plan-execution`, `CAP-PR-pull-request-delivery`,
`CAP-PR-operator-decisions` and `CAP-SDD-workflow-control`.

There is no universal deduplication promise for mutations. PR enrollment recovers
through `runs_list` filtered by project and exact PR number. After an uncertain
pause/cancel result, callers read state before retrying. Resume, Plan registration,
comments and connection starts use their domain-specific request identities.

### Connection-test views and bounded waits

`connection_tests_start` accepts `project_id`, `request_id`, optional
`ai_catalog_id` and optional `expected_project_revision >= 1`. The request ID is
also `test_id`. A matching existing request is replayed before the optional
revision check; a new request with a stale project revision conflicts. That field
does not pin independent catalog/connector changes.

`connection_tests_list` filters by catalog, test status or
`configuration_current` within the latest 30 retained project tests. Its default
limit is 10, permitted limit is 1–30, and `history_limit=30` makes the boundary
explicit. `total_count` is the matching count within that window; `next_offset`
continues it with the same filters. Concurrent additions can shift offset pages.
An older known test remains readable through `connection_tests_get`.

The public test view exposes only the recipe's approved evidence links and cleanup
notes, not its entire internal evidence map. `next_action` has this precedence:

1. Cleanup failed: `inspect_cleanup`.
2. Test is running or cleanup is not settled: `wait`.
3. Settled nonsuccessful result: `inspect_failure`.
4. Settled successful result: `done` if the fingerprint is current, otherwise
   `review_configuration`.

`runs_get` and `connection_tests_get` can wait for a state fingerprint change,
settlement or their bounded deadline. The implementation polls every two seconds;
settled values return immediately and waiting holds no database connection
between reads. Disconnecting a client does not cancel the underlying work.

## 5. Implementation and verification

Source inspected: `modules/hub/app/mcp/auth.py`, `modules/hub/app/mcp/server.py`,
`modules/hub/app/mcp/registration.py`, `modules/hub/app/mcp/contracts.py`,
the registration modules under `modules/hub/app/mcp/`,
`modules/hub/app/auth.py` and `modules/hub/app/main.py`.
The cited tests were inspected; this document does not assert that they or a
remote MCP client connection were executed during authoring.

Typed wrapper, page, preview and recovery coverage is in
`modules/hub/tests/integration/mcp/test_mcp.py` and
`modules/hub/tests/integration/mcp/test_work_decisions.py`; inputs and views are
defined in `modules/hub/app/mcp/contracts.py` and
`modules/hub/app/mcp/work_plans.py`. The two-second waiting interval is
source-inspected in `modules/hub/app/mcp/waiting.py`, not a live latency guarantee.
The [access operations guide](../../operations/access.md#mcp-connections) contains
credential/client setup and rotation procedures.
