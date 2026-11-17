---
id: UX-sdd-run
aliases: [UX-sdd-decision-history, UX-sdd-workflow-request]
title: SDD activity context
summary: "A pending question on an SDD activity run carries its unit, gate evidence and progress, while ordinary PR questions, controls and CI remain authoritative."
area: sdd
element: panel
status: active
usecases:
  - UC-complete-sdd-workflow
capabilities:
  - CAP-SDD-native-delivery
  - CAP-PR-pull-request-delivery
  - CAP-PR-operator-decisions
---

# [UX-sdd-run] SDD activity context

## 1. Purpose

- **Primary task**: decide the pending question of an SDD activity run with its evidence beside it.
- **Facts to commit**: Run/PR, unit/activity, the head the question is bound to and the current wait.

## 2. Content

This panel sits inside the pending Run question card of `UX-run-decisions`, below the question text; it is absent when no question is pending.

- Run question (heading "<Activity> gate · <unit>" for an agent question, "<Activity> question · <unit>" for an operator question; set by the question card).
- PR run (evidence line: the bound head, Open unit at this head and View PR changes).
- Run question (gate progress: Agent asked, Save an answer, Resume with the answer, Agent applies the decision; each step marked done, current step or not yet).
- PR run (note that the agent leaves the PR as a Draft and the operator marks it Ready in GitHub after the decision is applied).

The progress uses only the run and question reads. Draft/Ready and CI are not part of those reads, so delivery after the agent applies the decision stays outside the track. For an agent question, the answer editor placeholder names accept, request changes or reject as free-text guidance; Hub records no gate state. `UX-run-page` Related origins names the activity and current unit.

No native stage, runtime diagnostic, workflow-choice or integration-direction
control is offered. Draft indicates an operator merge decision is still required.

## 3. States

- **populated**: a pending question shows its evidence and current progress step; answer it in the question card.
- **saved**: the answer is saved and Resume with the answer is the current step.
- **applied**: the agent applies the decision; mark the Draft PR Ready in GitHub when it may merge.
- **loading/error**: use the `UX-run-decisions` refresh and retry feedback.
- **empty**: omit the panel when no question is pending or no descriptive snapshot exists; ordinary Run history remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open context / observe request and reply | `UC-complete-sdd-workflow` 1 | populated | populated | | `CAP-PR-pull-request-delivery` | Existing attempt progression remains visible. |
| Open unit at this head / View PR changes | `UC-complete-sdd-workflow` 4 | populated, saved | populated, saved | end | `CAP-SDD-native-delivery` | The unit at the bound head or the PR diff opens in GitHub in a new tab. |
| Open PR / observe CI | global: open the exact PR for readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | Exact GitHub PR and current-head CI outcome. |
