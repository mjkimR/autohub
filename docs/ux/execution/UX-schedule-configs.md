---
id: UX-schedule-configs
title: Schedule configurations screen
summary: "List schedule configurations, distinguish managed rows and let operators edit ordinary schedules or request a dispatcher tick."
area: execution
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UX-schedule-configs] Schedule configurations screen

## 1. Purpose

- **Primary task**: inspect and maintain Schedule configurations.
- **Facts to commit**: target task, cadence, enabled state, next run and whether another feature owns the configuration.
- **Secondary items**: creation/editing opens `UX-schedule-editor`; deletion opens `UX-schedule-delete`. The external-scheduler use case does not model this operator administration goal.

## 2. Content

The schedule table is primary at `/schedules/configs`. Search, enabled filtering, refresh, manual dispatch and creation controls sit above it.

- Schedule configuration (table row): name/description, task, cron or interval, enabled status and next-run time.
- System maintenance (managed row): protected management notice replaces ordinary row actions.
- Project connection and Connection test (owned row links, secondary weight): a dispatch row links "Project automation" to the project detail Automation tab (`/projects/<id>?tab=automation`), where the dispatch interval is edited; a connection-test row links "Project connections" to that project's Connections tab (`?tab=connections`). A row whose payload names no project (connection-test payloads carry only the test ID) links to the project list instead. Neither row offers toggle, edit or delete.
- Project connection (CI observation row link): a `pipeline.observe_project` row keeps toggle, edit and delete, and a "Project automation" link under its name opens its project's Automation tab, where the same schedule is listed, edited and deleted (`UX-project-detail`).
- Schedule configuration (other row actions): toggle, edit and delete; the editor is `UX-schedule-editor` and confirmation is `UX-schedule-delete`. Other project-managed tasks (`jules.session`, `jules.sync_sessions`) carry the managed badge while retaining these actions; their payload names no project, so the row cannot link to its owner, and the server refuses changes to a configuration an agent schedule owns (manage it in `UX-agent-schedules`).
- Schedule configuration (filter controls): search and All statuses/Active/Paused plus page navigation.
- Task specification (schema source): independently loaded for editor payload controls; its failure has a separate retry.

## 3. States

- **loading**: an initial empty table shows loading; refresh controls indicate progress.
- **populated**: inspect rows and use actions allowed for each task owner.
- **empty**: the table explains that no configurations match; change filters or create an ordinary configuration.
- **error**: list or task-specification loading shows its own Retry control; mutation failures are toasted.
- **triggering**: the manual dispatch control is busy until the tick response; the toast reports claimed count rather than individual job success.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh, search, filter or paginate | global: schedule administration is outside the external-scheduler use case | populated | loading |  | `CAP-EXEC-scheduling-maintenance` | The matching configurations reload; load failures remain distinguishable from no matches. |
| New Schedule or edit an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated | `UX-schedule-editor` | `CAP-EXEC-scheduling-maintenance` | The selected creation or edit form opens. |
| Enable or disable an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated |  | `CAP-EXEC-scheduling-maintenance` | Success or failure is toasted; successful changes refresh the list. |
| Delete an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated | `UX-schedule-delete` | `CAP-EXEC-scheduling-maintenance` | The named schedule and irreversible-action warning are shown. |
| Project automation (dispatch row) | global: change a project-owned dispatch cadence at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The project's Automation tab opens with the dispatch interval field (`UX-project-settings` automation region). |
| Project automation (CI observation row) | global: manage a project-owned CI observation at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The project's Automation tab opens with its owned schedules. |
| Project connections (connection-test row) | global: manage a project-owned verification at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The project's Connections tab opens, or the project list when the row names no project. |
| Trigger Dispatcher | global: schedule administration is outside the external-scheduler use case | populated | triggering |  | `CAP-EXEC-scheduling-maintenance` | The response toast reports the dispatched count and refreshes configurations. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | The selected screen replaces the schedule table. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.integration.test.ts`, including the owned-row link targets (Automation tab for dispatch and CI observation, Connections tab or project-list fallback for connection tests). Manual dispatch is not asserted to be the machine-identity flow in `UC-run-due-work`.
