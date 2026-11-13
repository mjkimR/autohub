---
id: PROP-schedule-config-ownership
title: Schedule configuration ownership and project filter
summary: "Expose the owning project and owner kind on schedule configuration reads and add a project filter to the list, so the schedule list links every owned row to its owner and the project screens stop deriving ownership from payloads."
status: draft                         # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: capabilities/execution/
priority: medium                      # critical | high | medium | low
size: M                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: medium               # low | medium | high (hint for Planning)
dev_effort: medium                    # low | medium | high (hint for Development)
boundaries:
  owns:
    - capabilities/execution/
    - capabilities/projects/
    - capabilities/agents/
    - ux/execution/
    - ux/projects/
    - modules/hub/app/features/scheduling/schedule_configs/
    - modules/hub/app/features/project_management/agent_schedules/
    - modules/hub/app/features/project_management/projects/
    - modules/hub/app/features/project_management/connection_tests/
    - modules/hub/migrations/
    - modules/hub/tests/
    - modules/hub-ui/src/lib/api/
    - modules/hub-ui/src/lib/features/scheduling/schedule-configs/
    - modules/hub-ui/src/lib/features/project-management/projects/
    - modules/hub-ui/src/lib/features/project-management/agent-schedules/
  excludes:
    - docs/decisions/
    - modules/hub/app/features/execution/
    - packages/sdk/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-schedule-config-ownership] Schedule configuration ownership and project filter

## 1. Background & Hypothesis

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

## 2. Technical Spike Questions

- **Q1 (derive or persist)**: Is the owner derived at read time (payload `project_id`, the agent-schedule reverse
  link, the connection test's `project_id` through `payload.test_id`) or persisted as columns on `schedule_configs`
  with a backfill migration? How does the list filter by project with either choice on PostgreSQL and SQLite, within
  the one-connection-per-request budget?
- **Q2 (owner vocabulary)**: Which owner kinds exist (installation maintenance, project dispatch, project CI
  observation, project agent schedule, legacy connection test, operator)? Is `jules.sync_sessions` operator-owned, as
  `CAP-AGENT-provider-sessions` rule 8 implies, and should the `PROJECT_MANAGED_TASKS` badge follow the owner instead
  of the task name?
- **Q3 (row actions)**: Does the read expose whether the generic list may change a row, so `ScheduleConfigsView`
  hides the actions the server refuses (agent-schedule rows) and links to the owner (`UX-agent-schedules`) instead?
- **Q4 (legacy connection-test rows)**: Are the legacy rows still worth an owner lookup, or does maintenance retire
  them so the frontend test-ID match can simply be dropped?

## 3. Proposed Design & Impact

Direction, to be settled in Planning:

1. **Backend**: `ScheduleConfigRead` gains an owner (kind, project ID, owner object ID) and
   `GET /api/v1/schedule_configs` gains a `project_id` filter; the managed-row guard in `ManagedScheduleHook` uses the
   same owner resolution.
2. **Schedule list**: `ScheduleConfigsView.svelte` links every owned row to its owner screen (Automation, Connections
   or `UX-agent-schedules`) and offers only the actions the owner allows.
3. **Follow-up simplification**: once the backend exists, `owned-schedules.ts` reads
   `GET /api/v1/schedule_configs?project_id=<id>` and drops the cross-project scan, the `payload.project_id` filter and
   the connection-test ID lookup; `OwnedSchedules.svelte` follows. `AgentSchedulesPanel.svelte` keeps its own API.

Expected impact: `CAP-EXEC-scheduling-maintenance` (schedule configuration read and list filters),
`CAP-AGENT-provider-sessions` and `CAP-PROJ-project-connections` where they state owned entries, `UX-schedule-configs`,
`UX-project-detail` (Automation tab owned schedules), typed client regeneration (`just gen-ui-api`), and a migration
if Q1 persists the owner.

Size: `M`. One feature spec: a read field, a filter and their two hub-ui consumers.

Non-goals:

1. Changing who may edit which schedule, or the 409 guards themselves.
2. Moving agent schedules or project dispatch onto a different storage model.
3. A cross-project schedule dashboard.

## 4. Lifecycle & Retirement Criteria
<!--
- Preliminary decisions: devkit spec proposal padr schedule-config-ownership "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept schedule-config-ownership --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff schedule-config-ownership.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->
