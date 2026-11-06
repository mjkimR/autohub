---
id: UX-work-plan-editor
title: Work Plan Editor
summary: "Create or revise Work Plan specifications and explicitly review fresh template-derived registrations with original-request recovery."
area: work-plans
element: panel
status: active
usecases:
  - UC-execute-work-plan
  - UC-reuse-work-plan-templates
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

### Template registration

Preserve the ordinary editor as the primary region. Add a source-template summary and fresh Item-key mapping above it. Omitted execution/history fields are disclosed, not copied. Default state is draft. A final Review registration disclosure shows the complete chosen execution state and current binding; active choice warns that eligible work can start immediately. Any payload/basis edit invalidates acknowledgement. Final labels distinguish Save draft, Submit proposal, Save ready plan and Register active work according to the chosen state. Session-storage notice explains that unresolved payload text remains in this account/project browser session until explicit dismissal, another reviewed operation or logout; known results survive remount.


## 3. States

- **populated**: enter fields, add/remove permitted Items and save or cancel.
- **empty**: a new draft can start without Items; add specifications before requesting executable work.
- **loading**: `Saving…` disables submission and structural controls.
- **error**: request/import errors remain inline; Item-key validation reports invalid or duplicate keys without redirecting dependency edges.
- **importing**: the task-list textarea and Use task list action are shown; a valid import fills the Item editors.

Template registration: **editing** can review/cancel; **confirming** can confirm or return to editing; **submitting** disables competing template writes; **conflict** shows old/current basis and requires re-review; **uncertain** retains original request across reload and permits only read-only checks/exact retry/close; **recorded** links original Plan/current state; **recorded-refresh-error** keeps acknowledgement and offers Refresh; **unavailable** offers Return to Templates; **error** retains unsent inputs and owner validation detail. Ordinary editor loading/empty behavior remains unchanged.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save draft / Submit proposal / Save ready plan / Add and start or schedule | `UC-execute-work-plan` 1, `UC-execute-work-plan` 2, `UC-execute-work-plan` 2c | populated, empty | loading | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Successful save closes the inline editor and reloads Plans; the chosen mode determines admission intent. |
| Correct rejected specification / retry same registration | `UC-execute-work-plan` 2a, `UC-execute-work-plan` 2b | error, populated | loading |  | `CAP-WORK-work-plan-execution` | Errors stay inline; retry of this form preserves its registration identity. |
| Add/remove Item / import task list | global: refine the local specification before saving | populated, empty, importing | populated, importing |  | `CAP-WORK-work-plan-execution` | Item editors and dependency choices update; invalid imports and keys show errors. |
| Cancel | global: leave the inline specification editor | populated, empty, error | populated | `UX-work-plans` |  | The parent Plan list remains without saving the edited form. |
| Review registration | `UC-reuse-work-plan-templates` 5 | editing | confirming |  | `CAP-WORK-work-plan-execution` | Complete payload, fresh keys, binding and state reviewed. |
| Edit input/basis | `UC-reuse-work-plan-templates` 5 | confirming | editing |  | `CAP-WORK-work-plan-execution` | Confirmation clears; original source snapshot is explicit. |
| Confirm Save draft / Register active work | `UC-reuse-work-plan-templates` 6 | confirming | submitting, recorded | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Retained receipt and current Plan link; active admission disclosure. |
| Correct invalid payload | `UC-reuse-work-plan-templates` 5a | error | editing |  | `CAP-WORK-work-plan-execution` | Owner error points to inputs; no automatic write. |
| Reload changed basis | `UC-reuse-work-plan-templates` 5b | conflict | editing |  | `CAP-WORK-work-plan-execution` | Old preview is removed and submission stays disabled until current template/binding and a new request/key mapping are loaded together. |
| Check original request / Retry same request | `UC-reuse-work-plan-templates` 6a, `UC-reuse-work-plan-templates` 6c | uncertain | uncertain, recorded |  | `CAP-WORK-work-plan-execution` | Same original operation/payload; missing read remains unknown. |
| Refresh acknowledged result | `UC-reuse-work-plan-templates` 6b | recorded-refresh-error | recorded, recorded-refresh-error |  | `CAP-WORK-work-plan-execution` | Recorded outcome remains distinct from refresh status. |
| Back to Templates | `UC-reuse-work-plan-templates` 4a | unavailable | populated | `UX-work-plan-templates` | `CAP-WORK-work-plan-execution` | No new execution or substituted source. |
| Cancel / Close | `UC-reuse-work-plan-templates` *a | editing, confirming, uncertain | populated | close |  | Return to parent; original unresolved intent survives. |

Original receipt controls stay in the parent `UX-work-plan-templates` panel after registration. Its Open original Plan action reveals the exact card in `UX-work-plans`; stale existing filters cannot hide that target.

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanForm.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
