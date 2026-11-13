---
id: UX-sdd-batch
title: Retained SDD batch history
summary: "The repository panel shows exact stored SDD batch selections, members and owner outcomes after live graph-based admission has been retired."
area: sdd
element: panel
status: active
usecases:
  - UC-execute-sdd-batch
capabilities:
  - CAP-SDD-native-delivery
---

# [UX-sdd-batch] Retained SDD batch history

## 1. Purpose

- **Primary task**: inspect one retained native batch.
- **Facts to commit**: exact batch/project, retired state, stored order and member/claim outcomes.
- **Secondary items**: detailed claim evidence and Run/PR links remain disclosures.

## 2. Content

- SDD batch (retired identity, state/revision, saved selection and detail).
- SDD unit (stored member intent and captured lineage).
- Native SDD activity (claim/checkpoint/outcome, linked Run/PR where retained).

No create, phase preference, pause/resume or next-admission control is shown.
Stored eligibility or graph fields are historical, not a current readiness claim.

## 3. States

- **populated**: inspect the selected retained batch and linked owners.
- **loading**: the exact detail is pending.
- **empty**: no retained batch is selected; load retained history if available.
- **error**: the exact ID is unavailable or its read failed; retry or browse.
- **retired**: explains that execution cannot resume; local Stop, where exposed by
  API, settles future admission only and cannot cancel external work.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Load/open exact batch | `UC-execute-sdd-batch` 1 | empty, populated | loading | | `CAP-SDD-native-delivery` | The exact retained selection loads. |
| Inspect members/claims | `UC-execute-sdd-batch` 2 | populated | populated | | `CAP-SDD-native-delivery` | Stored outcomes and uncertainty are visible. |
| Open owner | `UC-execute-sdd-batch` 3 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | Exact retained Run/PR opens. |
| Retry read / Browse repository | `UC-execute-sdd-batch` 1a | error | loading | `UX-repository` | `CAP-SDD-native-delivery` | No replacement subject is silently selected. |
