---
id: UX-schedule-editor
title: Schedule configuration editor
summary: "Create an ordinary schedule or edit its existing cadence, payload and activation through one mode-specific modal."
area: execution
element: modal
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UX-schedule-editor] Schedule configuration editor

## 1. Purpose

- **Primary task**: save a Schedule configuration.
- **Facts to commit**: schedule name, target task, cron/interval cadence and task payload. Existing task identity is fixed in edit mode.
- **Secondary items**: the task description helps interpret payload fields; Cancel returns to `UX-schedule-configs`.

## 2. Content

The form is the primary region; mode-specific title and controls distinguish creation from editing.

- Schedule configuration (identity fields): required name and optional description.
- Task specification (task selector): creation lists eligible task names; edit shows the fixed existing task. Creation excludes system.maintain, pipeline.connection_test and pipeline.dispatch_project.
- Schedule configuration (cadence): Cron Expression or Interval Seconds selects the corresponding input.
- Task specification (payload form): JsonSchemaForm renders the selected task schema when applicable.
- Schedule configuration (activation): Active Schedule is editable in edit mode.
- Footer: Cancel and Create Schedule/Save Changes.

## 3. States

- **create**: enter a required name and task, choose cadence and fill the payload before submission.
- **edit**: review prefilled values; the target task is disabled while name/cadence/payload/activation can change.
- **saving**: the submit button shows Saving; the edit Cancel control is disabled while submitting.
- **error**: validation or API failure is toasted and the form remains for correction.
- **closed**: successful save or cancellation removes the modal and returns to the list.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select Cron Expression or Interval Seconds | global: schedule administration is outside the external-scheduler use case | create | create |  |  | The corresponding cadence field appears without leaving the form. |
| Create Schedule or Save Changes | global: schedule administration is outside the external-scheduler use case | create | saving |  | `CAP-EXEC-scheduling-maintenance` | The request runs; success toasts, closes the modal and refreshes the parent list; failure leaves it open. |
| Cancel or dismiss | global: schedule administration is outside the external-scheduler use case | edit | closed | close |  | The modal closes without saving the draft. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleEditorDialog.svelte` and `modules/hub-ui/src/lib/features/scheduling/schedule-configs/schedule-form.ts`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.integration.test.ts`.
