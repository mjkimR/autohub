---
id: UX-work-plans
title: Project Work Plans
summary: "Inspect Work Plans and Items, control unstarted work and recover eligible unchanged failures through an inline disclosure. Current holds, prior outcomes and retained execution links remain visible."
area: work-plans
element: panel
status: active
usecases:
  - UC-execute-work-plan
  - UC-deliver-pull-request
capabilities:
  - CAP-WORK-work-plan-execution
  - CAP-PR-pull-request-delivery
---

# [UX-work-plans] Project Work Plans

## 1. Purpose

- **Primary task**: inspect and control project Work Plans.
- **Facts to commit**: Plan state, revision, target branch, schedule, dependency holds and which Work Items have started.
- **Secondary items**: editing opens an inline form; group classification and activity/comments remain subordinate to execution state.

## 2. Content

The filtered Plan list is primary. New/edit controls precede it; each card groups its own control actions, Work Items and retained activity.

- Work Plan (summary card): title, saved group, revision, target branch, scheduled start, state and predecessor Plans.
  - Work Item (expandable row): key, title, branch/state, waiting reason, specification, acceptance and dependencies.
  - Work Item (recovery disclosure): original failure/target, eligibility and next action; reason, confirm/cancel, accepted/hold/reconciliation status and paged recovery history are subordinate to the Item. Successful sibling outcomes remain visible.
  - Work Item (execution links): PR, Issue and `UX-pipeline-runs`; expired Run history is distinguished from retained completion evidence.
  - Work Plan (mirror status): Issue link, pending/error state separate from execution.
  - Work Plan (activity/comment region): author/time/revision, change details, comments filter and further-page loading.
- Work Plan (editor): `UX-work-plan-editor`.
- Work Plan (group editor): classification-only field; current group and concurrent revision warning remain visible.

Filters include All, Next work, Needs a decision, Execution requested, On hold/paused and Finished, plus exact group selection. Background refresh pauses while an editor or control is active.

## 3. States

- **populated**: inspect Plans and Work Items, filter, refresh or use applicable controls.
- **empty**: no matching Plans; change filters or Add plan.
- **loading**: initial Plan loading text; wait for records.
- **error**: load/control failure is visible; refresh or correct/retry the operation.
- **editing**: a Plan or group editor is visible; finish/cancel before automatic refresh resumes.
- **busy**: a Plan control is pending and competing controls are disabled.

- **confirming**: retry disclosure shows unchanged-work scope, original PR/target and prior failure; enter a reason or cancel. Successful Items and budget counters remain retained.
- **accepted**: acceptance is confirmed; refresh current status or inspect history.
- **awaiting-admission**: show the current recovery hold detail for schedule, dependencies, enabled project, catalog/quota or capacity; refresh status. Retry is unavailable while pending.
- **reconciling**: show that the prior external outcome must be known before fresh work; refresh or check the original request.
- **running**: retain the Run link and progress; inspect execution or close the disclosure.
- **refused**: show refusal/detail and supported next action; inspect the evidence before a fresh confirmation.
- **history-empty**: show no invented recovery attempts; retain current outcome and applicable actions.
- **history-loading**: keep Item context visible while status/history loads.
- **response-uncertain**: preserve the immutable request identity across remounts; check the original request or refresh history instead of submitting another command.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Add plan / Edit | `UC-execute-work-plan` 1, `UC-execute-work-plan` 2c | populated, empty | editing | `UX-work-plan-editor` | `CAP-WORK-work-plan-execution` | An inline form opens; edits are offered only before Items start. |
| Inspect saved Plan, Items and waits / Refresh | `UC-execute-work-plan` 2, `UC-execute-work-plan` 3, `UC-execute-work-plan` 4, `UC-execute-work-plan` 5, `UC-execute-work-plan` 6, `UC-execute-work-plan` 7, `UC-execute-work-plan` 3a | populated, loading | populated |  | `CAP-WORK-work-plan-execution` | States, waiting reasons, retained outcomes and mirror evidence reflect loaded records. |
| Inspect preparation or delivery attention | `UC-execute-work-plan` 4a, `UC-execute-work-plan` 4b, `UC-execute-work-plan` 5a, `UC-execute-work-plan` 5b, `UC-execute-work-plan` 7a | populated | populated |  | `CAP-WORK-work-plan-execution` | Actual detail/state and independent mirror failure remain visible. |
| Start / Pause / Resume | `UC-execute-work-plan` 2c, `UC-execute-work-plan` 6a | populated | busy |  | `CAP-WORK-work-plan-execution` | A successful control reloads the Plan; refused controls show an error. |
| Revoke and confirm | `UC-execute-work-plan` 6b | populated | busy |  | `CAP-WORK-work-plan-execution` | Confirmation states that started work continues and this Plan cannot resume. |
| Submit a stale control | `UC-execute-work-plan` *a | populated | error |  | `CAP-WORK-work-plan-execution` | The error preserves the server state; reload before deciding whether to retry. |
| Open Execution runs | global: follow an admitted Work Item to its PR delivery | populated | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | The project Runs tab opens. |
| Change group / save / cancel | global: update classification without controlling execution | populated, editing | editing, populated |  | `CAP-WORK-work-plan-execution` | The saved group and any conflicting revision are shown; errors retain the form. |
| Expand activity / add comment / load more | global: inspect or add explanatory Plan history | populated | populated |  | `CAP-WORK-work-plan-execution` | Activity changes load separately; comments do not start work or answer Run questions. |
| Retry Work Item / Confirm retry | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c, `UC-deliver-pull-request` *d | populated, confirming | confirming, busy | | `CAP-WORK-work-plan-execution` | Review the prior result and unchanged target, enter a reason and receive acceptance or refusal. |
| Refresh recovery / Check original request | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c, `UC-deliver-pull-request` *d | busy, accepted, awaiting-admission, reconciling, response-uncertain, error | awaiting-admission, reconciling, running, refused | | `CAP-WORK-work-plan-execution` | Current hold detail and original request/history resolve response loss without duplicate acceptance. |
| Inspect recovery history / Load more | `UC-execute-work-plan` 7 | populated, history-empty | populated | | `CAP-WORK-work-plan-execution` | Paged prior outcomes, actor/reason/time, ordered events and retained execution links remain distinguishable. |
| Cancel recovery disclosure | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c | confirming | populated | close | `CAP-WORK-work-plan-execution` | Return to the Item without sending a command. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlansPanel.svelte`
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkItemRecovery.svelte`
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkItemRecovery.integration.test.ts`
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanGroup.svelte`
- `modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlanActivity.svelte`

The content and transitions are derived from source inspection. Executed UI interaction checks are recorded in `docs/materials/2026-11/20261105-work-item-retry/development-checks.md`. This document
does not assert a browser walkthrough or live GitHub/provider verification.
