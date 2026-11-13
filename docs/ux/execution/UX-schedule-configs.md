---
id: UX-schedule-configs
title: Schedule configurations screen
summary: "Filter schedules by project, inspect verified owners and use server-permitted generic actions or open the owning project."
area: execution
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
  - CAP-PROJ-project-connections
  - CAP-AGENT-provider-sessions
---

# [UX-schedule-configs] Schedule configurations screen

## 1. Purpose

- **Primary task**: inspect and maintain Schedule configurations.
- **Facts to commit**: target task, cadence, enabled state, next run and whether another feature owns the configuration.
- **Secondary items**: creation/editing opens `UX-schedule-editor`; deletion opens `UX-schedule-delete`. The external-scheduler use case does not model this operator administration goal.

## 2. Content

The schedule table is primary at `/schedules/configs`. Search, Project, enabled filtering, refresh, manual dispatch and creation controls sit above it. Project defaults to All projects; changing search/status/project resets pagination.

- Schedule configuration (table row): name/description, task, cron or interval, enabled status and next-run time.
- Schedule configuration (owner fact): server owner metadata supplies System Managed or Project Managed badges, independently of task-name guesses. System maintenance shows its protected management notice.
- Project connection (owner link): verified dispatch/observation owners link Project automation to Automation; linked agent owners link Agent schedules to the same tab. Retained test owners link Project connections to Connections. The resolved project name appears beside the row and in the accessible link name; its verified ID is the fallback when options cannot name it.
- Schedule configuration (unresolved owner): Owner unavailable replaces an invented destination. Protected rows offer no generic toggle/edit/delete; no link falls back to the project list.
- Schedule configuration (generic actions): only generic_mutation_allowed rows show toggle, edit and delete. Unlinked provider tasks are ordinary operator rows. The editor is `UX-schedule-editor`; confirmation is `UX-schedule-delete`.
- Project connection (filter options): an independent paginated project read supplies names. Retry recovers option failures without changing the selected value or loading configurations; Refresh reloads configurations, task specifications and options. Earlier option responses cannot overwrite the latest read.
- Task specification (schema source): independently loaded for editor payload controls; its failure has a separate retry.

## 3. States

- **loading**: an initial empty table shows loading; refresh controls indicate progress.
- **populated**: inspect rows and use actions allowed for each task owner.
- **empty**: the table explains that no configurations match; change filters or create an ordinary configuration.
- **error**: list or task-specification loading shows its own Retry control; mutation failures are toasted.
- **project-options-error**: a separate Retry reports the options failure. The selected project remains and the unfiltered list/other filters stay usable; previously loaded names remain available.
- **triggering**: the manual dispatch control is busy until the tick response; the toast reports claimed count rather than individual job success.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh, search, filter or paginate | global: schedule administration is outside the external-scheduler use case | populated | loading |  | `CAP-EXEC-scheduling-maintenance` | The matching configurations reload; project/search/status changes reset page one and retain composed filters. Load failures remain distinguishable from no matches. |
| New Schedule or edit an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated | `UX-schedule-editor` | `CAP-EXEC-scheduling-maintenance` | The selected creation or edit form opens. |
| Enable or disable an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated |  | `CAP-EXEC-scheduling-maintenance` | Success or failure is toasted; successful changes refresh the list. |
| Delete an ordinary row | global: schedule administration is outside the external-scheduler use case | populated | populated | `UX-schedule-delete` | `CAP-EXEC-scheduling-maintenance` | The named schedule and irreversible-action warning are shown. |
| Project automation (dispatch row) | global: change a project-owned dispatch cadence at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The project's Automation tab opens with the dispatch interval field (`UX-project-settings` automation region). |
| Project automation (CI observation row) | global: manage a project-owned CI observation at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The project's Automation tab opens with its owned schedules. |
| Project connections (connection-test row) | global: manage a project-owned verification at its owner | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The verified project's Connections tab opens; unresolved owners have no link. |
| Agent schedules | global: manage a verified agent-owned configuration at its project | populated | populated | `UX-project-detail` | `CAP-AGENT-provider-sessions` | The project Automation tab opens with `UX-agent-schedules`; no exact-row selection is implied. |
| Retry project options | global: recover filter options independently | project-options-error | populated |  | `CAP-EXEC-scheduling-maintenance` | Options reload; selection stays unchanged and failure remains explicit. |
| Trigger Dispatcher | global: schedule administration is outside the external-scheduler use case | populated | triggering |  | `CAP-EXEC-scheduling-maintenance` | The response toast reports the dispatched count and refreshes configurations. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | The selected screen replaces the schedule table. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.integration.test.ts`, including verified owner names/links, unavailable owners, permitted action visibility, project-filter reset/composition, option-error retry and stale-response selection preservation. Manual dispatch is not asserted to be the machine-identity flow in `UC-run-due-work`.
