---
id: UX-work-plan-editor
title: Work Plan Editor
summary: "Create or revise an inline Work Plan specification with dependencies, schedule and an explicit draft, proposed, held or execution-requested state."
area: work-plans
element: panel
status: active
usecases:
  - UC-execute-work-plan
capabilities:
  - CAP-WORK-work-plan-execution
---

# [UX-work-plan-editor] Work Plan Editor

## 1. Purpose

- **Primary task**: specify a Work Plan and its Work Items.
- **Facts to commit**: Plan intent, target branch, state, scheduled start, dependencies and each executable Item specification/acceptance.
- **Secondary items**: optional JSON import and group classification support the specification without becoming execution policy.

## 2. Content

The Plan fields precede its dependency choices and Item editors. Save mode is explicit before creation; the final button describes whether the write holds work or requests execution.

- Work Plan (specification form): title, target branch, group key, goal/scope, optional local-time start and predecessor Plans.
- Work Item (editor row): key, title, specification, acceptance and dependencies on other Items in this Plan.
  - Work Item (bulk import): JSON task array when the form permits structural edits.
- Work Plan (save mode): Draft, Proposed, Ready/on hold or Start/request execution for creation.
- Work Plan (edit reason): optional reason on updates; an edited proposal returns to Draft.

Drafts can omit executable detail. Active work requires complete executable input. Item keys/dependencies can be structurally changed only where the source permits flexible draft/proposed editing.

## 3. States

- **populated**: enter fields, add/remove permitted Items and save or cancel.
- **empty**: a new draft can start without Items; add specifications before requesting executable work.
- **loading**: `Saving…` disables submission and structural controls.
- **error**: request/import errors remain inline; Item-key validation reports invalid or duplicate keys without redirecting dependency edges.
- **importing**: the task-list textarea and Use task list action are shown; a valid import fills the Item editors.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save draft / Submit proposal / Save ready plan / Add and start or schedule | `UC-execute-work-plan` 1, `UC-execute-work-plan` 2, `UC-execute-work-plan` 2c | populated, empty | loading | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Successful save closes the inline editor and reloads Plans; the chosen mode determines admission intent. |
| Correct rejected specification / retry same registration | `UC-execute-work-plan` 2a, `UC-execute-work-plan` 2b | error, populated | loading |  | `CAP-WORK-work-plan-execution` | Errors stay inline; retry of this form preserves its registration identity. |
| Add/remove Item / import task list | global: refine the local specification before saving | populated, empty, importing | populated, importing |  | `CAP-WORK-work-plan-execution` | Item editors and dependency choices update; invalid imports and keys show errors. |
| Cancel | global: leave the inline specification editor | populated, empty, error | populated | `UX-work-plans` |  | The parent Plan list remains without saving the edited form. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanForm.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
