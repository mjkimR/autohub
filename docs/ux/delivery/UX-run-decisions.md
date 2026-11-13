---
id: UX-run-decisions
title: Run Decisions
summary: "The Decisions panel of a PR run separates saved Run question answers, explicit resumption and read-only native history while retaining current run context and history. Supports exact pending-decision navigation."
area: delivery
element: panel
status: active
usecases:
  - UC-resolve-run-question
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
capabilities:
  - CAP-PR-operator-decisions
  - CAP-PR-pull-request-delivery
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
---

# [UX-run-decisions] Run Decisions

## 1. Purpose

- **Primary task**: Resolve a Run question or inspect a historical native decision.
- **Facts to commit**: Current PR run revision, wait reason, pending question, saved answers and native evidence.
- **Secondary items**: Native evidence stays in read-only disclosures; prior questions and approval activity are secondary history.
- **Hosts**: the Decisions section of `UX-run-page`, and the Decision inbox review dialog in `UX-decision-inbox`, which adds the PR identity, Inspect pull request, Open run page and Close around this panel.

## 2. Content

The current wait and Run question form are primary. Retired native evidence is
secondary history; it provides no live workflow controls.

- PR run (last successful local load time with Refresh decisions; in the inbox dialog also the wait reason and terminal notice, which `UX-run-page` shows in its header and next-step section instead).
- Run question (pending text, saved answer list, application state).
  - Run question (Your answer editor with Save and resume and Save only; collapsed as Answer differently while a saved answer awaits resume).
  - Run question (reasoned dismissal; inside a disclosure).
- Run question (earlier-question history with Previous/Next pagination).
- `UX-sdd-run` (descriptive activity context or read-only retired evidence).
- `UX-sdd-decision-history` (native approval/publication activity).

Only the latest history page offers actions. Loading compares question and run
revisions; mismatched data requires refresh rather than enabling stale controls.
Saving an answer does not resume; selecting a saved answer is a separate action.

### Answer composer

When the parent supplies a save operation, the question card owns the answer
editor. Save and resume issues two owner requests: it saves the answer, then
resumes with that saved answer explicitly selected; Save only stops after the
save. An unconfirmed save keeps the text and sends no resume. If the resume
fails, or the saved answer cannot be identified, the answer stays saved, the run
stays paused and the card explains that the saved answer's Resume with this
answer is the next step. While an unapplied saved answer exists, its resume is
the primary action and the editor collapses under Answer differently.

The decision outcome region appears only for a retained submission or read
subject. Otherwise the browser-reload explanation is a collapsed secondary
disclosure that does not lead the decision content.

Inbox entry supplies an exact current Run question identity. Historical native
requests never become actionable through inbox inspection. A changed or resolved selection cannot inherit editors or authority. After an acknowledged mutation the inbox reloads its current cursor page before owner reload; a resolved selection remains disabled. Closing restores the originating row or nearest remaining row and retains filters.

The selected decision outcome is retained beside its owner controls. It identifies the exact displayed request, saved answer text, applied attempt and independent delivery/publication evidence. Current Run/authority/hold remains distinct. Another history selection changes the displayed read subject without replacing an unresolved mutation intent. Parent review owns PR navigation and Close.

## 3. States

- **populated**: Current decisions are loaded; select the applicable answer or action.
- **empty**: No pending question; eligible nonterminal runs offer Ask and pause, and stopped runs can offer inspected recovery.
- **loading**: Latest decisions load; actions stay disabled until the run/question revisions agree.
- **error**: An inline alert explains the failure; Refresh decisions reloads current evidence.
- **busy**: A save/resume locks competing actions until it settles.
- **terminal**: Ended runs retain evidence and history; inspect the PR and register replacement work when needed.

- **saved**: Saved text/identity remains visible; applying a saved answer requires explicit selection.
- **applied**: The retained attempt is shown separately from delivery and current pause/terminal state.
- **uncertain**: Outcome unknown offers Check outcome and eligible Retry same request; replacement submission is disabled while original intent exists.
- **changed**: Changed basis disables old continuation; refresh current context before another action.
- **acknowledged-refresh-error**: Recorded identity/text survives failed refresh; retry reads rather than replacing the mutation.
- **retired**: native evidence is inspect-only; no workflow answer, approval or publication retry is offered.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh decisions | `UC-resolve-run-question` 1, `UC-decide-sdd-proposal` 1 | populated | loading |  | `CAP-PR-operator-decisions` | Current run/questions replace the inspected basis or show a conflict. |
| Save answer / Save only | `UC-resolve-run-question` 2 | populated | busy |  | `CAP-PR-operator-decisions` | A status confirms that the answer is saved and the run remains stopped. |
| Save and resume | `UC-resolve-run-question` 2, `UC-resolve-run-question` 4 | populated | busy, saved |  | `CAP-PR-operator-decisions` | The answer is saved, then applied by a separate resume naming it; a failed resume leaves it saved with the run paused. |
| Resume with saved answer | `UC-resolve-run-question` 4, `UC-complete-sdd-workflow` 5 | populated | busy |  | `CAP-PR-operator-decisions` | The selected answer is applied or a refusal is shown; delivery may remain pending. |
| Ask and pause | `UC-resolve-run-question` 1a | empty | busy |  | `CAP-PR-operator-decisions` | The question is recorded and progression is blocked. |
| Dismiss without resuming | `UC-resolve-run-question` 4c | populated | busy |  | `CAP-PR-operator-decisions` | The dismissal is retained; execution remains stopped. |
| Resume after inspection | global: recover a stopped run without granting native integration authority | empty | busy |  | `CAP-PR-pull-request-delivery` | The current run is reloaded; no integration approval is implied. |
| Previous / Next questions | global: inspect retained question history without changing execution | populated | loading |  | `CAP-PR-operator-decisions` | The selected history page loads; older-page actions are disabled. |
| Close (inbox dialog) | global: leave decision inspection without submitting further direction | populated | populated | close |  | The Decision inbox remains visible with its row focused. |
| Open run page (inbox dialog) | global: continue from an inbox review to the run's home | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The PR run page opens. |

Last loaded identifies the last successful consistent Run/question read. A failed refresh keeps that prior observation time. Outcome API observation and persisted record times are separate facts.

### Retained outcome actions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Check outcome / Check saved answer outcome | global: inspect the exact saved owner request | uncertain | saved, applied, uncertain | | `CAP-PR-operator-decisions` | Exact selected request is read; missing records/read errors remain unknown. |
| Retry same request | global: recover an uncertain ordinary submission | uncertain | applied, uncertain, changed | | `CAP-PR-operator-decisions` | Original ordinary request and payload replay only; owner guards remain authoritative. |

Embedded panels retain the visible parent context and its Close exit; they add no Back button. Native history can select a retained request outcome for reading only.

## 5. Evidence

- [RunDecisions.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisions.svelte) (panel) and [RunDecisionsDialog.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.svelte) (inbox dialog host).
- [DecisionQuestion.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionQuestion.svelte) and [DecisionAnswerComposer.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionAnswerComposer.svelte).
- [DecisionOutcome.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionOutcome.svelte).
- [DecisionQuestion.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionQuestion.integration.test.ts) and [DecisionOutcome.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionOutcome.integration.test.ts).
- [RunDecisionsDialog.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
