---
id: UX-sdd-run
aliases: [UX-sdd-decision-history, UX-sdd-workflow-request]
title: SDD activity context
summary: "The Run panel shows descriptive SDD activity intent while ordinary PR questions, controls and CI remain authoritative."
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

- **Primary task**: follow the ordinary PR Run.
- **Facts to commit**: Run/PR, unit/activity, current wait.

## 2. Content

- Native SDD activity (descriptive unit/activity/effort).
- PR run (existing state, PR link and ordinary controls in their existing primary region).
- Run question (existing question/answer/explicit-resume UI).
- Execution attempt (existing request/reply timeline).

No native stage, runtime diagnostic, workflow-choice or integration-direction
control is offered. Draft indicates an operator merge decision is still required.

## 3. States

- **populated**: follow the ordinary Run and its PR.
- **waiting**: use the existing question editor and selected-answer resume.
- **loading/error**: use existing refresh/retry feedback.
- **empty**: omit the activity panel when no descriptive snapshot exists; ordinary Run history remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open context / observe request and reply | `UC-complete-sdd-workflow` 1 | populated | populated | | `CAP-PR-pull-request-delivery` | Existing attempt progression remains visible. |
| Open PR / observe CI | global: open the exact PR for readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | Exact GitHub PR and current-head CI outcome. |
