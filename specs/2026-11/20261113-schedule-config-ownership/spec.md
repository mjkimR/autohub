---
id: SPEC-schedule-config-ownership
title: Schedule configuration ownership and project filter
summary: Expose the owning project and owner kind on schedule configuration reads and add a project filter to the list, so the schedule list links every owned row to its owner and the project screens stop deriving ownership from payloads.
status: planned
created: 2026-11-13
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---
<!-- devkit:skeleton -->

# [SPEC-schedule-config-ownership] Schedule configuration ownership and project filter

## 1. Problem Statement & Motivation

Handed off from proposal PROP-schedule-config-ownership on 2026-11-13.
- **Preserved Materials**: `docs/materials/2026-11/20261113-schedule-config-ownership`
- Target Docs Blueprint: `PROP-schedule-config-ownership-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

A schedule configuration (`ScheduleConfig`, `modules/hub/app/features/scheduling/schedule_configs/models.py`) has no
owner field. Ownership lives in three different places, and the hub-ui reconstructs it per screen:

- **Project dispatch and CI observation** (`pipeline.dispatch_project`, `pipeline.observe_project`): the payload
  carries `project_id` (`modules/hub/app/features/project_management/projects/repos.py` writes it and filters on
  `ScheduleConfig.payload["project_id"]`).
- **Agent schedules** (`jules.session`): `ProjectAgentSchedule.schedule_config_id`
  (`modules/hub/app/features/project_management/agent_schedules/models.py`) points at the config, but
  `session_payload` (`agent_schedules/repos.py`) writes only catalog, repository, branch, title, prompt and work type;
  the project appears only inside the generated config name (`_config_name`, "Agent <id>: <title> (<project>)").
  `AgentScheduleRepository.owner_of_config` finds the owner only server-side.
- **Legacy connection tests** (`pipeline.connection_test`): the payload carries only `test_id`
  (`ConnectionTestPayload`, task in `modules/hub/app/features/execution/tasks/domains/pipeline/connection_probe.py`);
  current tests advance through system maintenance, so these rows exist only for tests started before that.

What the hub-ui derives today:

- `modules/hub-ui/src/lib/features/project-management/projects/owned-schedules.ts` `loadOwnedSchedules` reads every
  `pipeline.*` configuration across all projects (`GET /api/v1/schedule_configs?task_func=pipeline.`, paged through
  `allPages`) and filters by `payload.project_id` in the browser, because the list has no project filter (the filters
  in `schedule_configs/query_options.py` are `search`, `name`, `task_func` and `enabled`). For legacy connection-test
  rows it adds a second read, `GET /api/v1/projects/{project_id}/connection-tests`, and matches `payload.test_id`
  against that project's test IDs (the connection-test project lookup gap). `OwnedSchedules.svelte` renders the
  result in the project Automation tab.
- `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte` keeps a hard-coded
  `PROJECT_MANAGED_TASKS` set and builds owner links from `payload.project_id`. A legacy connection-test row falls
  back to `/projects`. A `jules.session` row carries the "Project Managed" badge but no owner link, and still offers
  Pause, Edit and Delete, which `ManagedScheduleHook._refuse_if_managed`
  (`schedule_configs/services.py`) refuses with 409 "managed by a project agent schedule; edit or delete it there";
  `ScheduleConfigsView.integration.test.ts` asserts that error toast. `UX-schedule-configs` documents both gaps ("their
  payload names no project, so the row cannot link to its owner"; "A row whose payload names no project ... links to
  the project list instead").
- `modules/hub-ui/src/lib/features/project-management/agent-schedules/AgentSchedulesPanel.svelte` lists agent
  schedules through the separate `GET /api/v1/projects/{project_id}/agent-schedules`, whose use case
  (`agent_schedules/usecases.py`) joins the owned config's `task_func` and timing; ownership there comes from the
  route, not from the config.

Hypothesis: one server-side owner on the schedule configuration read (owner kind, project and owner object ID) and a
`project_id` list filter let the schedule list link and guard every owned row, and let the project screens read their
schedules with one filtered request instead of a cross-project scan and a test-ID match.

## 2. User Stories

- **US-1**: As a developer/agent, I want to implement Schedule configuration ownership and project filter so that system capabilities are extended.

## 3. Non-Goals

1. **Scope Excluded**: <what this change will not do>

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] <scenario>
- **Given** <precondition>
- **When** <action>
- **Then** <expected result>

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Planning Decisions

Evidence was inspected at source HEAD `e1a50a8064597d65fd44906f1b65c01ad93c2425`; no product tests or live service
checks were run in Planning. `ADR-schedule-owner-projection` compares derived reads with persisted owner columns.

| Question | Settled direction | Consequence |
| --- | --- | --- |
| Q1: derive or persist | Derive from existing task identity, payload and owner relationships. Add no owner columns or backfill. | Reads use a bounded page projection and the existing request session; PostgreSQL and SQLite need filter parity tests. |
| Q2: vocabulary | Return `owner.kind`, nullable `owner.project_id` and nullable `owner.object_id` using the table below. | A provider task name alone does not prove project ownership. An unlinked `jules.session` and `jules.sync_sessions` are operator-owned. |
| Q3: actions | Return `generic_mutation_allowed` independently of ownership. | CI observation remains generically mutable. Reserved maintenance, dispatch, connection-test tasks and agent-owned entries retain their existing HTTP 409 protection. |
| Q4: retained tests | Resolve retained connection-test ownership through `payload.test_id` on the server. Do not delete these configurations. | The browser no longer needs a separate connection-test read, including its current 30-test history limit. |

#### Read contract and resolution order

All responses using `ScheduleConfigRead`, including successful create/patch/put responses, contain the same
read-only owner projection and `generic_mutation_allowed` boolean. Neither field is a writable ownership assertion.
The existing read fields and mutation request shapes remain compatible.

Apply this table top to bottom. `object_id` names the existing owning object, rather than the schedule configuration.
Resolve IDs against retained rows; missing, malformed or dangling payload references produce null owner IDs without
failing the whole list. A reserved task remains protected even when its owner cannot be resolved.

| Condition | `owner.kind` | `project_id` / `object_id` | Generic mutations |
| --- | --- | --- | --- |
| `system.maintain` | `system_maintenance` | null / null | false |
| `pipeline.dispatch_project` | `project_dispatch` | retained payload project / same project | false |
| `pipeline.connection_test` | `connection_test` | retained test's project / retained test | false |
| Remaining configuration linked by `ProjectAgentSchedule.schedule_config_id` | `project_agent_schedule` | schedule's project / agent schedule | false |
| Remaining `pipeline.observe_project` | `project_observation` | retained payload project / same project | true |
| Everything else | `operator` | null / null | true |

The existing create/retarget checks for reserved task names remain in place. Reuse a shared classification policy
for read action metadata and the existing guard; do not make protection conditional on resolving a project.
An unlinked provider-session task remains an ordinary operator configuration, matching existing backend authority.
The owner projection is navigation metadata, not an authorization grant.

#### Query and layer design

- Keep `Router → UseCase → Service → Repository`. Repositories resolve database relationships; a service assembles
  owner metadata and action policy. Routers return the typed read model without performing queries.
- Fetch page owner metadata in batches through the same caller-owned `AsyncSession`. Do not construct a dependency
  that checks out another connection. Detail and mutation reads use the same projector with a one-row batch.
- `project_id` is an optional UUID list filter. Apply it before pagination and counting; compose it with existing
  search, enabled, task and ordering filters. A valid unknown project returns an empty page and count zero.
  Invalid UUID syntax returns the existing FastAPI validation response, HTTP 422.
- The filter follows the resolution precedence above. Use correlated existence predicates for owner rows rather than
  fan-out joins that duplicate configurations. Compare payload UUID text safely across SQLite and PostgreSQL;
  malformed JSON values must not reach a database UUID cast that can fail the request. Test canonical and unhyphenated
  UUID text and exclude references that do not resolve to a retained owner.
- A counted page uses at most five SQL statements independent of page size: count and page selection, then up to
  three bounded lookup batches for agent schedules, connection tests and referenced projects. A `skip_count` read
  omits the count. Test the bound at 1 and 50 returned rows with every owner kind, on both supported databases.
  This is an implementation acceptance bound, not a Planning performance measurement.
- SQL statements remain sequential on one session; no per-row owner queries, parallel sessions or external reads.
  No new feature dependency edge is intended: scheduling already imports these project-management owners in its
  mutation guard. If enforcing architecture checks identify a new edge, return it to the Host before expanding scope.

### 3. Proposed Design & Impact

#### Delivery scope

1. Enrich `ScheduleConfigRead` and implement the filtered, bounded owner projection without changing stored rows.
2. Replace `ScheduleConfigsView.svelte` task-name badges/action decisions with server ownership and mutation metadata.
   Add a Project filter beside existing filters. Show the resolved project name on each project-owned row and in its
   owner link accessible name; fall back to the verified project ID when project options are unavailable. Resolve
   owner links from verified IDs: Automation for dispatch,
   observation and agent schedules; Connections for legacy tests. For an unresolved protected owner show
   `Owner unavailable`, with no fabricated link and no generic mutation actions.
3. Make `owned-schedules.ts` request `GET /api/v1/schedule_configs?project_id=<id>` with pagination. Partition
   dispatch, observation and connection-test rows by `owner.kind`; ignore agent-owned configurations in this panel
   because `AgentSchedulesPanel.svelte` retains its dedicated API. Drop the all-project scan and test-ID matching.
4. Update the owning capability and UX documents from the ledger and Screens in `target-docs.md`. Promote only
   `ADR-schedule-owner-projection` into `docs/decisions/` at handoff; no other decision edits are in scope.

The generic list links an agent-owned entry to the existing project's Automation section. Selecting or scrolling
to one exact agent schedule is excluded; the returned owner ID preserves a future addressing option without
adding a separate deep-link mechanism here.

#### Acceptance examples

- **OWNER-01**: Given each owner kind and an unlinked `jules.session`/`jules.sync_sessions`, when list, detail or a
  successful mutation returns a configuration, then its owner and generic mutation flag follow the resolution table.
- **OWNER-02**: Given two projects and mixed owner kinds, when the list filters one project with search, enabled,
  ordering and pagination, then both count and rows cover only that project's resolved configurations without
  duplicates. Unknown projects return empty; malformed UUID query values return 422.
- **OWNER-03**: Given dangling or malformed payload IDs, when the list or detail is read, then it succeeds with null
  IDs for unresolved ownership. Reserved tasks remain immutable and project filtering excludes unresolved owners.
- **OWNER-04**: Given agent-owned, reserved and editable observation/operator configurations, when the operator
  inspects their rows, then only allowed generic mutation actions appear and owner links target the correct project
  tab. Rows with similar configuration names in two projects show distinct project identities and accessible owner
  links. A crafted mutation still receives the existing 409 protection for managed configurations.
- **OWNER-05**: Given a project with more than 30 retained connection tests and a legacy schedule naming an older
  retained test, when Automation loads schedules, then the server returns that configuration and the browser uses no
  cross-project configuration scan or separate connection-test request.
- **OWNER-06**: Given counted pages of 1 and 50 configurations spanning all kinds, when the API reads them on SQLite
  and PostgreSQL, then it checks out at most one request connection and issues at most five SQL statements per read.
- **OWNER-07**: Given the schedule list Project filter, when the operator selects or clears a project, then pagination
  resets to the first page and the request composes `project_id` with existing filters. A failed project-options load
  has a retry and leaves the unfiltered list usable.

#### Verification plan

Backend HTTP coverage extends schedule-config API tests, existing project-dispatch protection tests and agent
schedule tests. Add malformed/dangling IDs, cross-database UUID matching, count/pagination parity and query/connection
budget coverage. UI integration coverage extends `ScheduleConfigsView.integration.test.ts` and project owned-schedule
loading tests to check links, action absence/presence, filter reset and exact request parameters. Regenerate and check
the typed client with `just gen-ui-api` and `just check-ui-api`.

Development runs targeted SQLite and PostgreSQL coverage, affected frontend tests, then repository `just lint` and
`just check`. The source inventory in `MAT-schedule-owner-evidence` distinguishes inspected tests
from actual execution. Size remains `M`; Development effort remains `medium` because this adds a public read contract
and both API and UI consumers.

#### Non-goals

1. **Scope Excluded**: changing generic schedule mutation authority, task execution, due-time logic or existing 409 guards.
2. **Scope Excluded**: owner columns, migrations, backfills, automatic legacy-row retirement or a schedule storage rewrite.
3. **Scope Excluded**: a cross-project schedule dashboard, new agent-schedule APIs or exact agent/test deep-link selection.
4. **Scope Excluded**: unrelated provider migration and decisions beyond the single owner-projection PADR.

### 4. Lifecycle & Retirement Criteria

Planning settles the read direction and delivery scope. `plan-accept` remains pending the Host's review and the user's
acceptance. No API implementation, mutation, migration, acceptance or handoff occurs in this Planning turn.
No deferred product work is required to satisfy OWNER-01 through OWNER-07.

