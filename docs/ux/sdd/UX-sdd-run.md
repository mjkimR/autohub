---
id: UX-sdd-run
title: Native SDD Run
summary: "The native run panel presents inspected workflow evidence, holds and integration authority separately from PR readiness and ordinary resume. Safe diagnostic classifications explain recovery without executing advice. Supports exact pending-decision navigation."
area: sdd
element: panel
status: active
usecases:
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
---

# [UX-sdd-run] Native SDD Run

## 1. Purpose

- **Primary task**: Review native execution evidence and choose integration direction.
- **Facts to commit**: Bound SDD unit, inspected head/base, workflow stage, reports, holds and existing authority.
- **Secondary items**: Worker/workflow requests and publication history are linked panels; repository evidence opens in GitHub.

## 2. Content

Current next action and integration evidence are primary. Reports and verified
stage details provide supporting evidence; destructive/withdrawal actions are
behind Other actions or an explicit feedback editor.

- Native SDD activity (next action, current workflow, verified stages and warnings).
- SDD unit (bound path and head/base evidence link).
- Native SDD activity (Planning evidence/reports for proposal units; execution
  reports for spec units).
- Native SDD activity (worker problems and pending questions).
- Native SDD activity (Devkit diagnostics with code/severity, responsibility category, summary, next step, static file targets and read-only retry guidance; unmatched historical warnings remain visible).
- Native SDD activity (integration authority and PR-draft status shown separately).
- `UX-sdd-workflow-request` (current request before integration decisions).
- `UX-sdd-decision-history` (approval/publication history in the parent dialog).

Diagnostic guidance is read-only. Reinspect after repair describes a recovery condition, not an automatic retry or another decision action. Safe generic guidance represents unknown diagnostics; the panel does not display raw stderr through diagnostic records.

Pending Hub questions disable integration decisions. Request changes requires
nonblank feedback. Stop run and Withdraw approval expose their effect before the
operator confirms the specific action.

Inbox entry supplies the exact integration/request identity through the parent review. Refreshed persisted evidence is required before controls enable. Existing hold, revision and authority checks remain applicable.

The selected decision outcome is retained beside its owner controls. It identifies the exact displayed request, saved answer text, applied attempt and independent delivery/publication evidence. Current Run/authority/hold remains distinct. Another history selection changes the displayed read subject without replacing an unresolved mutation intent. Parent review owns PR navigation and Close.

## 3. States

- **populated**: Inspect evidence and use the action offered for the current wait.
- **empty**: Evidence/report absence is stated; inspect the repository or refresh the parent before deciding.
- **held**: Worker problems, pending questions or runtime/receipt diagnostics explain the required recovery; approval is not a bypass.
- **editing**: A revise/reject/revoke editor names the effect; submit or cancel the editor.
- **busy**: A decision is applying; competing controls are disabled.
- **error**: The inline decision error retains the inspected context; refresh through the parent before changing the basis.
- **terminal**: The completed/failed/canceled execution remains inspectable with no active integration controls.

- **saved**: Saved text/identity remains visible; applying a saved answer requires explicit selection.
- **applied**: The retained attempt is shown separately from delivery and current pause/terminal state.
- **uncertain**: Outcome unknown offers Check outcome and eligible Retry same request; replacement submission is disabled while original intent exists.
- **changed**: Changed basis disables old continuation; refresh current context before another action.
- **acknowledged-refresh-error**: Recorded identity/text survives failed refresh; retry reads rather than replacing the mutation.
- **publication-pending**: Exact worker answer remains recorded; duplicate answer controls stay disabled without matched publication proof.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Inspect evidence | `UC-decide-sdd-proposal` 1, `UC-complete-sdd-workflow` 4 | populated | populated | end | `CAP-SDD-workflow-control` | The bound unit at the inspected head opens in GitHub. |
| Approve integration | `UC-complete-sdd-workflow` 4 | populated | busy |  | `CAP-SDD-workflow-control` | Refreshed evidence shows the retained authority or an error. |
| Request changes / Send change request | `UC-complete-sdd-workflow` 4b | populated | editing |  | `CAP-SDD-workflow-control` | The requested direction and refreshed stopped/rework state are visible. |
| Withdraw approval / Revoke approval | `UC-complete-sdd-workflow` 4c | populated | editing |  | `CAP-SDD-workflow-control` | The editor names withdrawal; refreshed evidence shows the resulting authority. |
| Stop run / Reject and stop | `UC-complete-sdd-workflow` 4d | populated | editing |  | `CAP-SDD-workflow-control` | The editor warns that already dispatched work may continue; the resulting run state is loaded. |
| Cancel editor | global: abandon an unsubmitted native decision | editing | populated |  | `CAP-SDD-workflow-control` | The editor closes and its unsubmitted feedback clears. |

### Retained outcome actions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Check outcome | `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | uncertain | saved, applied, uncertain | | `CAP-PR-operator-decisions` | Exact selected request is read; missing records/read errors remain unknown. |
| Retry same request | `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 5b | uncertain | applied, uncertain, changed | | `CAP-SDD-workflow-control` | Original request and payload replay only; current owner guards remain authoritative. |

Embedded panels retain the visible parent context and its Close exit; they add no Back button. Native history owns Check request outcome and sends its exact read subject to the parent outcome region.

## 5. Evidence

- [SddRunPanel.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddRunPanel.svelte).
- [SddDiagnostics.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddDiagnostics.svelte).
- [SddNextAction.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddNextAction.svelte).
- [SddPlanningEvidence.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddPlanningEvidence.svelte).
- [SddReports.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddReports.svelte).
- [SddRunPanel.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddRunPanel.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
