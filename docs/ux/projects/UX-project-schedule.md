---
id: UX-project-schedule
title: CI Observation Schedule
summary: "Create or edit a project's CI observation schedule (observed PR numbers, interval or cron trigger, enabled flag) from the project's Automation section."
area: projects
element: modal
status: active
usecases:
  []
capabilities:
  - CAP-EXEC-scheduling-maintenance
  - CAP-PR-ci-observation
  - CAP-PROJ-project-connections
---

# [UX-project-schedule] CI Observation Schedule

## 1. Purpose

- **Primary task**: configure one project CI observation Schedule configuration.
- **Facts to commit**: project, observed PR numbers, name, interval/cron trigger and enabled state.
- **Secondary items**: the project's dispatch schedule is not created here; it is derived from the project and
  follows the dispatch interval in `UX-project-settings`.

## 2. Content

The PR numbers come first, then the name and description, then the trigger. Save and Cancel follow the form.

- Project connection (fixed subject): supplies the project identifier written to the payload.
- PR observation (input): comma-separated positive PR numbers; the dialog refuses an empty list.
- Schedule configuration (form): name, optional description, Interval (seconds, with 1 min / 5 min / 15 min / 1 h
  presets) or Cron (UTC), and the enabled flag. Edit mode loads the selected schedule's values.
- Saved Schedule configuration: success closes the dialog and reloads the owned schedules in `UX-project-detail`;
  the same row also appears in `UX-schedule-configs`.

## 3. States

- **populated**: complete inputs, submit or cancel.
- **loading**: submission is disabled while saving.
- **error**: invalid PR input or a request failure produces a toast; correct inputs or leave the dialog.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Create schedule / Save changes | global: maintain a project-owned scheduler entry at its owner | populated | loading | close | `CAP-EXEC-scheduling-maintenance`, `CAP-PR-ci-observation` | Success closes with a toast and the owned schedules reload; a refused request keeps the dialog and reports the server message. |
| Cancel / dismiss | global: leave schedule configuration | populated, error | populated | close |  | The project's Automation section remains available. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectScheduleDialog.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/OwnedSchedules.svelte`

Inspected check: `ProjectDetailView.integration.test.ts` creates a CI observation for the project (no dispatch
option) and edits an existing one with its loaded PR numbers. The content and transitions are derived from source
inspection. This document does not assert live GitHub verification.
