---
id: UX-sdd-run
title: SDD activity context
summary: "The Run panel shows descriptive SDD activity intent and retained legacy evidence while ordinary PR questions, controls and CI remain authoritative."
area: sdd
element: panel
status: active
usecases:
  - UC-complete-sdd-workflow
  - UC-decide-sdd-proposal
capabilities:
  - CAP-SDD-native-delivery
  - CAP-PR-pull-request-delivery
  - CAP-PR-operator-decisions
  - CAP-SDD-workflow-control
---

# [UX-sdd-run] SDD activity context

## 1. Purpose

- **Primary task**: follow the ordinary PR Run or inspect retired native evidence.
- **Facts to commit**: Run/PR, unit/activity, current wait and whether the snapshot is retired.
- **Secondary items**: legacy reports/decisions remain read-only disclosures.

## 2. Content

- Native SDD activity (descriptive unit/activity/effort).
- PR run (existing state, PR link and ordinary controls in their existing primary region).
- Run question (existing question/answer/explicit-resume UI).
- Execution attempt (existing request/reply timeline).
- Native SDD activity (retired evidence disclosure for a legacy snapshot).

No native stage, runtime diagnostic, workflow-choice or integration-direction
control is offered. Draft indicates an operator merge decision is still required.
A legacy retirement notice explains that previously dispatched external work may
still exist and must be inspected before replacement.

## 3. States

- **populated**: follow the ordinary Run and its PR.
- **waiting**: use the existing question editor and selected-answer resume.
- **retired**: inspect stored evidence only; native execution cannot resume.
- **loading/error**: use existing refresh/retry feedback.
- **empty**: explain that no native evidence exists; ordinary Run history remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open context / observe request and reply | `UC-complete-sdd-workflow` 1 | populated | populated | | `CAP-PR-pull-request-delivery` | Existing attempt progression remains visible. |
| Open PR / observe CI | global: open the exact PR for readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | Exact GitHub PR and current-head CI outcome. |
| Inspect retired history | `UC-complete-sdd-workflow` 1a, `UC-decide-sdd-proposal` 1, `UC-decide-sdd-proposal` 2 | retired | retired | `UX-sdd-decision-history` | `CAP-SDD-workflow-control` | Stored evidence opens without authority. |
| Open Run/PR or leave history | `UC-decide-sdd-proposal` 3, `UC-decide-sdd-proposal` 1a | retired | populated | `UX-run-page` | `CAP-SDD-native-delivery` | Exact available owner opens or its absence is explained. |
