---
id: UX-sdd-decision-history
title: Retained SDD decision history
summary: "The history panel lists stored native decision receipts and publication evidence without retrying or reconciling former workflow effects."
area: sdd
element: panel
status: active
usecases:
  - UC-decide-sdd-proposal
capabilities:
  - CAP-SDD-workflow-control
  - CAP-SDD-native-delivery
---

# [UX-sdd-decision-history] Retained SDD decision history

## 1. Purpose

- **Primary task**: inspect a recorded native decision.
- **Facts to commit**: action, actor, time, captured head/base and recorded outcome.
- **Secondary items**: expanded evidence remains a disclosure.

## 2. Content

- Native SDD activity (retired label).
- Recorded decision (stored action/actor/feedback and publication evidence).
- PR run (retained exact Run/PR links).

Historical publication state is evidence, not a pending operation to resend.
There is no native answer, approval, publication-retry or reconciliation control.

## 3. States

- **populated**: expand recorded evidence or open the owner.
- **loading**: history is being fetched.
- **empty**: no retained decision receipts exist.
- **error**: retry the read; no write follows a failed read.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Load / expand history | `UC-decide-sdd-proposal` 1, `UC-decide-sdd-proposal` 2 | populated, empty | populated | | `CAP-SDD-workflow-control` | Stored receipts are shown as retired evidence. |
| Open owner / close disclosure | `UC-decide-sdd-proposal` 3, `UC-decide-sdd-proposal` 1a | populated, error | populated | `UX-run-page` | `CAP-SDD-native-delivery` | Exact available Run/PR opens; unavailable evidence is explained. |
