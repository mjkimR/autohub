---
id: UX-project-schedule
title: Create Scheduled Automation
summary: "Configure a project dispatcher or CI observation schedule with an interval or cron trigger and inspect whether creation is accepted."
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

# [UX-project-schedule] Create Scheduled Automation

## 1. Purpose

- **Primary task**: configure a project Schedule configuration.
- **Facts to commit**: project, task kind, name, interval/cron trigger and observation PR numbers when selected.
- **Secondary items**: explanatory dispatch/observation text stays beside the task-kind choice.

## 2. Content

The task-kind choice precedes task-specific inputs and trigger controls. Save and Cancel follow the form.

- Project connection (fixed subject): supplies the project identifier.
- Schedule configuration (form): dispatcher or CI observation, name, description, interval presets/seconds or cron expression.
  - PR observation (input): comma-separated positive PR numbers only for observation.
- Saved Schedule configuration: creation success closes the modal; the generic schedule list is `UX-schedule-configs`.

The source still offers a dispatcher choice; the server's protected project-owned-dispatcher rule can refuse generic dispatcher creation. The dialog reports that refusal rather than promising a second dispatcher.

## 3. States

- **populated**: choose the task and trigger, complete inputs, submit or cancel.
- **loading**: submission is disabled while scheduling.
- **error**: invalid observation PR input or request failure produces a toast; correct inputs or leave the dialog.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Create Schedule | global: save a project-specific automation schedule | populated | loading | close | `CAP-EXEC-scheduling-maintenance`, `CAP-PROJ-project-connections` | Success closes with a toast; invalid/protected schedule requests keep the dialog and report failure. |
| Cancel / dismiss | global: leave schedule configuration | populated, error | populated | close |  | The originating project view remains available. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectScheduleDialog.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
