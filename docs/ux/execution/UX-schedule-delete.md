---
id: UX-schedule-delete
title: Schedule deletion confirmation
summary: "Require an explicit confirmation before deleting a named ordinary schedule while explaining that prior schedule-job history remains."
area: execution
element: modal
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UX-schedule-delete] Schedule deletion confirmation

## 1. Purpose

- **Primary task**: confirm removal of the selected Schedule configuration.
- **Facts to commit**: the schedule name, irreversible deletion and preservation of past Schedule job history.
- **Secondary items**: Cancel returns to `UX-schedule-configs`; task ownership and eligible row actions remain with that parent.

## 2. Content

The selected schedule name and consequence warning are primary; Cancel and Delete Schedule follow them.

- Schedule configuration (deletion subject): the selected name is emphasized.
- Schedule configuration (consequence notice): this action cannot be undone.
- Schedule job (retention notice): existing execution history is preserved.
- Schedule configuration (conditional ownership warning): the component can display a project-managed warning, system maintenance, project-dispatch and connection-test rows omit deletion, while some legacy project-managed task rows can still reach this warning.

## 3. States

- **populated**: review the selected identity and choose deletion or cancellation.
- **deleting**: Delete Schedule shows Deleting and both footer controls are disabled.
- **error**: a failed request is toasted and the named confirmation remains open for retry or cancellation.
- **closed**: success or cancellation removes the modal.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Delete Schedule | global: schedule administration is outside the external-scheduler use case | populated | deleting |  | `CAP-EXEC-scheduling-maintenance` | Success closes the modal and reloads the parent; failure leaves the confirmation available. |
| Cancel or dismiss | global: schedule administration is outside the external-scheduler use case | populated | closed | close |  | The named schedule is retained. |

## 5. Evidence

Implementation inspected: the deletion dialog in `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.integration.test.ts`.
