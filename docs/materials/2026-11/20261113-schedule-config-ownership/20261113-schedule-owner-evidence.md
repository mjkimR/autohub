---
id: MAT-schedule-owner-evidence
title: Schedule ownership source evidence
summary: "Planning inventory of existing schedule ownership, generic mutation protection and read costs at source HEAD e1a50a8; separates inspected enforcement from checks executed."
created_at: 2026-11-13
---

# [MAT-schedule-owner-evidence] Schedule ownership source evidence

Source basis: `e1a50a8064597d65fd44906f1b65c01ad93c2425`.

| Inspected source | Observation used in the design |
| --- | --- |
| `schedule_configs/schemas.py`, `query_options.py`, `usecases/crud.py`, `api/v1.py` under `modules/hub/app/features/scheduling/` | Read uses generic CRUD and exposes no owner or project filter. Enriching only list/detail would leave successful mutation responses inconsistent. |
| `schedule_configs/services.py` | `_refuse_owned_task` protects maintenance, project dispatch and legacy test task names; `_refuse_if_managed` also protects reverse-linked agent configurations. CI observation is not forbidden. |
| `project_management/projects/repos.py` | Dispatch and observation identify projects using payload text. No separate owner column exists. |
| `project_management/agent_schedules/models.py`, `repos.py` | Unique `schedule_config_id` gives the agent-schedule owner. Session payload contains repository/catalog fields, not project ID. |
| `project_management/connection_tests/models.py`, `repos.py` | Retained tests have project IDs. The browser-facing project list reads only 30 tests, so it is not an ownership index for all retained test IDs. |
| `CAP-AGENT-provider-sessions` rule 8 and `test_an_operator_sync_entry_for_the_catalog_is_left_alone` | `jules.sync_sessions` can be operator-owned and is not made project-owned by its task name. |
| `owned-schedules.ts`, `OwnedSchedules.svelte` | Browser scans `pipeline.*` configuration pages and separately matches retained tests. Agent schedules already have their own panel/API. |
| `UX-schedule-configs`, `UX-agent-schedules` and their Svelte implementations | Generic screen currently has task-name-based badges and actions; Automation is the existing owner landing region. |

Paths without a full prefix in the table's project-management rows are under `modules/hub/app/features/`.

Inspected enforcement includes schedule-config CRUD API tests, project dispatch authority tests and agent-schedule
owned-entry refusal tests. No product tests, database query benchmarks, frontend browser checks or live deployment
checks were executed in Planning. The at-most-five SQL/one-connection bound is a planned acceptance check;
Development must demonstrate it on SQLite and PostgreSQL.

Read projection was selected over persisted owner fields because the requested outcome is read/navigation behavior;
persistence would add cross-writer synchronization and a data migration. No owner storage change is required to
satisfy the acceptance examples.
