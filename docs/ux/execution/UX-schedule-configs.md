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
- Project connection and Connection test (owned row notices): dispatch/verification schedules direct the operator to the owning project feature.
- Schedule configuration (other row actions): toggle, edit and delete; the editor is `UX-schedule-editor` and confirmation is `UX-schedule-delete`. Legacy project-managed tasks can carry the managed badge while retaining these actions.
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
| Trigger Dispatcher | global: schedule administration is outside the external-scheduler use case | populated | triggering |  | `CAP-EXEC-scheduling-maintenance` | The response toast reports the dispatched count and refreshes configurations. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | The selected screen replaces the schedule table. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.integration.test.ts`. Manual dispatch is not asserted to be the machine-identity flow in `UC-run-due-work`.
