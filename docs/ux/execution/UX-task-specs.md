---
id: UX-task-specs
title: Registered task specifications screen
summary: "Show registered task descriptions and payload schemas so an operator can understand the tasks available to schedule configuration."
area: execution
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UX-task-specs] Registered task specifications screen

## 1. Purpose

- **Primary task**: inspect a registered Task specification.
- **Facts to commit**: task name, description and any declared payload schema.
- **Secondary items**: search narrows the loaded list; scheduling changes remain in `UX-schedule-configs`.

## 2. Content

At `/operations/tasks`, a card collection is primary below Refresh and name/description search.

- Task specification (card): registered name, task badge and description or No description provided.
- Task specification (schema representation): formatted read-only JSON appears only when the task exposes a payload schema.
- Task specification (search): locally filters task names and descriptions; no execution control is shown.

## 3. States

- **loading**: Loading task specifications is shown; await the request.
- **populated**: inspect cards and refine search.
- **empty**: No task specifications registered is shown for an empty result, including when the local filter matches none; clear search or refresh.
- **error**: LoadError offers Retry while List unavailable distinguishes request failure from an empty registry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or Retry | global: inspect operational state without starting the underlying work | populated | loading |  | `CAP-EXEC-scheduling-maintenance` | Registered task specifications reload or an error message appears. |
| Search task specifications | global: inspect operational state without starting the underlying work | populated | populated |  |  | Cards update from the already loaded collection. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | The selected administration screen appears. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/execution/task-specs/TaskSpecsView.svelte` and `modules/hub-ui/src/routes/operations/tasks/+page.svelte`. Registry behavior is specified in `CAP-EXEC-scheduling-maintenance`; this document records no executed browser check.
