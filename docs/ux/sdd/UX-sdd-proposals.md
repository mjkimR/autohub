---
id: UX-sdd-proposals
title: SDD activity intent
summary: "A selected proposal exposes explicit Planning or Development intent beside its document, with unit status, a local start outcome and workspace-level request recovery."
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
- **Secondary items**: preferences are disclosed on demand; the unit status summary, related runs and existing-PR enrollment belong to `UX-sdd-execution`.

## 2. Content

The selected document is primary in `UX-repository`. This form occupies the selected SDD unit's work panel beside the document on wide screens and below it on narrow screens. No duplicate proposal execution list appears above the viewer.

- SDD unit (the selected proposal directory).
- PR run (unit status from `UX-sdd-execution`, above the form when the unit has PR runs).
- Native SDD activity (Planning/Development selector, editable Activity base branch and optional effort preferences).
- Native SDD activity (review summary of activity, base, unit and Draft PR effect).
- PR run (owner notice when a non-final PR run of the selected activity already holds the unit: PR number, state and Open PR #N).
- Native SDD activity (explicit Start Planning or Start Development; secondary weight while an owner notice is shown).
- Native SDD activity (local start outcome below Start: unresolved-request notice, titled refusal or registered confirmation).
- SDD activity claim (`UX-sdd-claim-recovery`, accessed from the workspace request outcome on an ownership conflict).

Activity base defaults to the document branch and remains independently editable. A different base is disclosed in the review summary. Changing the selected unit or browse branch resets the editable activity form. Document status remains descriptive metadata; it never gates Planning or Development. Repository setup and workflow are the working agent's responsibility.

The owner notice is non-blocking: Start stays enabled because Hub's activity admission, not the form, refuses a competing start. When the owning run owes the operator a decision, the unit status's Open decisions stays the single primary action.

The original request recovery is mounted above both repository viewer modes. It identifies the original unit/activity/base or PR; request identity, effort and catalog sit in its Request details disclosure. A retained owner shows only the `UX-sdd-claim-recovery` card, not a separate request card. It never changes to match a subsequently selected document. Exact-request retry uses the retained payload.

The local start outcome sits below Start for the unit the request named:

- While a request is unresolved, it names the original activity and unit, explains why new starts are unavailable and offers Review the original request, which moves focus to the workspace recovery.
- A definitive refusal is a titled alert that states nothing was published and the request is closed. An existing activity branch is named with Inspect branch on GitHub; a project configuration refusal offers Open Connections and Open Settings.
- Successful registration confirms the activity and offers Open PR run.

Focus moves to the local outcome only when a request settles while the panel is open.

## 3. States

- **populated**: review activity/base and submit explicit intent.
- **unselected**: select a proposal through `UX-repository`; no activity form is shown for an ordinary file or spec.
- **loading**: starting work retains the reviewed request and disables competing starts.
- **owned**: a non-final PR run of the selected activity holds the unit; follow it through Open PR #N or Open decisions, or start explicitly and let Hub decide admission.
- **refused**: a definitive refusal (input, configuration or an existing activity branch without a retained claim) closes the request and clears the project's start lock; resolve the named cause, then start again.
- **uncertain**: the workspace retains original intent and Retry same request; the local outcome links to it. Selecting another document or Git Browser does not erase recovery or permit competing work.
- **ownership-conflict**: inspect the original owner through `UX-sdd-claim-recovery`; an active owner offers retained Run/PR inspection.
- **reconciliation-required**: an uncertain no-Run reservation retains the explicit inspected-external-work acknowledgment before release.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select proposal/activity/base | `UC-start-sdd-activity` 1 | unselected, populated | populated | | `CAP-SDD-native-delivery` | The exact unit/activity/base review summary updates. |
| Start activity | `UC-start-sdd-activity` 2, `UC-start-sdd-activity` 3, `UC-start-sdd-activity` 4 | populated, owned | loading | | `CAP-SDD-native-delivery` | Workspace feedback retains the submitted intent and original request identity; the settled outcome appears below Start. |
| Open PR #N (owner notice) | `UC-start-sdd-activity` 2b | owned | owned | `UX-run-page` | `CAP-SDD-native-delivery` | The owning PR run opens. |
| Review the original request | `UC-start-sdd-activity` 3b | uncertain, ownership-conflict | uncertain, ownership-conflict | | `CAP-SDD-native-delivery` | Focus moves to the workspace request recovery. |
| Inspect branch on GitHub / Open Connections / Open Settings | `UC-start-sdd-activity` 2a, `UC-start-sdd-activity` 3a | refused | refused | end | `CAP-SDD-native-delivery` | The named branch or project configuration opens; the closed request is not retried. |
| Retry same request | `UC-start-sdd-activity` 3b, `UC-start-sdd-activity` 4a | uncertain | loading | | `CAP-SDD-native-delivery` | The identical request checks/reconciles its original outcome. |
| Inspect conflicting owner | `UC-start-sdd-activity` 2b, `UC-start-sdd-activity` 3a | ownership-conflict, reconciliation-required | populated | `UX-sdd-claim-recovery` | `CAP-SDD-native-delivery` | Exact retained owner/evidence opens. |
| Open PR run | `UC-start-sdd-activity` 5 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The original registered Run opens. |
| Select another document | global: inspect another subject without replacing a submitted request | populated, error, uncertain | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Editable intent follows the selection; submitted request recovery remains at workspace level. |

## 5. Evidence

`SddProposals.integration.test.ts` covers selected-unit targeting, reviewed base, context resets and exact-request recovery. `SddUnitPanel.integration.test.ts` covers the owner notice, the local outcome, refusal classification and focus. The checks use simulated API responses; rendered browser and live GitHub behavior remain separate verification boundaries.
