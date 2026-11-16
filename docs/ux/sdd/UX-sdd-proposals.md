---
id: UX-sdd-proposals
title: SDD activity intent
summary: "A selected proposal exposes explicit Planning or Development intent beside its document, with reviewed unit/base and workspace-level request recovery."
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

- **Primary task**: request explicit work for the proposal being read.
- **Facts to commit**: proposal directory, activity, base and optional effort.
- **Secondary items**: preferences are disclosed on demand; related runs and existing-PR enrollment belong to `UX-sdd-execution`.

## 2. Content

The selected document is primary in `UX-repository`. This form occupies the selected SDD unit's work panel beside the document on wide screens and below it on narrow screens. No duplicate proposal execution list appears above the viewer.

- SDD unit (the selected proposal directory).
- Native SDD activity (Planning/Development selector, editable Activity base branch and optional effort preferences).
- Native SDD activity (review summary of activity, base, unit and Draft PR effect; explicit Start Planning or Start Development).
- SDD activity claim (`UX-sdd-claim-recovery`, accessed from the workspace request outcome on an ownership conflict).

Activity base defaults to the document branch and remains independently editable. A different base is disclosed in the review summary. Changing the selected unit or browse branch resets the editable activity form. Document status remains descriptive metadata; it never gates Planning or Development. Repository setup and workflow are the working agent's responsibility.

The original request outcome is mounted above both repository viewer modes. It identifies the original unit/activity/base or PR, effort and request identity. It never changes to match a subsequently selected document. Exact-request retry uses the retained payload. Successful registration offers Open PR run.

## 3. States

- **populated**: review activity/base and submit explicit intent.
- **unselected**: select a proposal through `UX-repository`; no activity form is shown for an ordinary file or spec.
- **loading**: starting work retains the reviewed request and disables competing starts.
- **error**: a definitive input refusal exposes the error; correct the form and submit explicitly.
- **uncertain**: the workspace retains original intent and Retry same request; selecting another document or Git Browser does not erase recovery or permit competing work.
- **ownership-conflict**: inspect the original owner through `UX-sdd-claim-recovery`; an active owner offers retained Run/PR inspection.
- **reconciliation-required**: an uncertain no-Run reservation retains the explicit inspected-external-work acknowledgment before release.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select proposal/activity/base | `UC-start-sdd-activity` 1 | unselected, populated | populated | | `CAP-SDD-native-delivery` | The exact unit/activity/base review summary updates. |
| Start activity | `UC-start-sdd-activity` 2, `UC-start-sdd-activity` 3, `UC-start-sdd-activity` 4 | populated | loading | | `CAP-SDD-native-delivery` | Workspace feedback retains the submitted intent and original request identity. |
| Retry same request | `UC-start-sdd-activity` 3b, `UC-start-sdd-activity` 4a | uncertain | loading | | `CAP-SDD-native-delivery` | The identical request checks/reconciles its original outcome. |
| Inspect conflicting owner | `UC-start-sdd-activity` 2b, `UC-start-sdd-activity` 3a | ownership-conflict, reconciliation-required | populated | `UX-sdd-claim-recovery` | `CAP-SDD-native-delivery` | Exact retained owner/evidence opens. |
| Open PR run | `UC-start-sdd-activity` 5 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The original registered Run opens. |
| Select another document | global: inspect another subject without replacing a submitted request | populated, error, uncertain | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Editable intent follows the selection; submitted request recovery remains at workspace level. |

## 5. Evidence

`SddProposals.integration.test.ts` covers selected-unit targeting, reviewed base, context resets and exact-request recovery. The checks use simulated API responses; rendered browser and live GitHub behavior remain separate verification boundaries.
