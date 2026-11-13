---
id: UX-sdd-proposals
title: SDD activity intent
summary: "The proposals panel presents descriptive repository units and starts explicit Planning or Development intent without a readiness gate."
area: sdd
element: panel
status: active
usecases:
  - UC-start-sdd-activity
capabilities:
  - CAP-SDD-native-delivery
---

# [UX-sdd-proposals] SDD activity intent

## 1. Purpose

- **Primary task**: start one explicit repository activity and open its PR Run.
- **Facts to commit**: project/repository, unit, base, activity and optional effort/catalog.
- **Secondary items**: retained Run/PR links stay below each unit; historical batches are a separate disclosure.

## 2. Content

The selected activity intent is primary. Status is descriptive metadata, not a
Hub-verified eligibility result. Repository setup and workflow are the working
agent's responsibility.

- SDD unit (path/title/status on the selected base).
- Native SDD activity (Planning/Development, base and effort/catalog preferences).
- PR run (tracked Run and exact GitHub PR links).
- SDD batch (read-only retained-history disclosure).
- `UX-sdd-claim-recovery` (exact retained owner inspection and explicit acknowledgment; on an ownership conflict).

No runtime card, readiness preview, acceptance/rejection control or executable
milestone selection appears here.

## 3. States

- **populated**: choose explicit intent or open an existing Run.
- **loading**: the current request is in flight; competing starts are unavailable.
- **empty**: select a document through **Browse repository**.
- **error**: retain the selection and original request; retry the exact request.
- **uncertain**: show the original unit/base/activity/preferences and request identity;
  **Check original request**/**Retry same request** recover only that intent.
  Browsing another document does not erase this disclosure or permit a competing start.
- **ownership-conflict**: identify/link the active Run or retained claim; inspect that
  owner rather than retrying as replacement work.
- **reconciliation-required**: identify retained evidence and explain that inspected
  external work must be explicitly acknowledged before a retired reservation is released.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select unit/activity/base | `UC-start-sdd-activity` 1 | populated | populated | | `CAP-SDD-native-delivery` | Exact intent is shown. |
| Start activity / Retry same request | `UC-start-sdd-activity` 2, `UC-start-sdd-activity` 3, `UC-start-sdd-activity` 4, `UC-start-sdd-activity` 3b | populated, error, uncertain | loading | | `CAP-SDD-native-delivery` | Original request identity is retained. |
| Inspect conflicting owner | `UC-start-sdd-activity` 2b, `UC-start-sdd-activity` 3a | ownership-conflict, reconciliation-required | populated | `UX-sdd-claim-recovery` | `CAP-SDD-native-delivery` | The exact retained owner/evidence opens. |
| Open run | `UC-start-sdd-activity` 5, `UC-start-sdd-activity` 4a | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact registered Run opens. |
| Browse repository | global: leave execution selection | empty, error, populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | The document browser opens. |
