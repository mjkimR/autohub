---
id: UX-sdd-execution
title: Enroll repository activity work
summary: "The selected SDD unit shows its status per activity, its PR runs and a secondary existing-PR enrollment disclosure with an initially empty PR number."
area: sdd
element: panel
status: active
usecases:
  - UC-complete-sdd-workflow
  - UC-inspect-repository-documents
capabilities:
  - CAP-SDD-native-delivery
  - CAP-PR-pull-request-delivery
  - CAP-DOC-repository-viewer
---

# [UX-sdd-execution] Enroll repository activity work

## 1. Purpose

- **Primary task**: see what currently holds the selected SDD unit and follow its PR runs.
- **Facts to commit**: unit path, exact Run/PR; enrollment additionally requires an explicitly entered positive integer PR number and takes an optional effort.
- **Secondary items**: Enroll an existing PR is a collapsed disclosure inside the unit work panel. Its button is labeled Enroll PR.

## 2. Content

- SDD unit (selected directory and document branch; changing unit/branch resets the enrollment form).
- PR run (unit status, shown when the unit has PR runs: the latest PR run per activity with its state badge and PR link; Open decisions on a paused or blocked run).
- PR run ("PR runs for this unit" rows, newest first, with independent loading/empty/error state and exact Run/PR links).
- PR run (secondary enrollment disclosure, empty Pull request field, activity effort defaulting to Use repository recommendation with Low, Medium or High, and Enroll PR).

Unit status sits above the activity form, so owed work is seen before a new start. The newest PR run that owes the operator carries the only primary Open decisions; other owed runs show it at secondary weight.

A history row opens the run's Decisions section only while the run is paused or blocked; otherwise it opens the Run page. The list shows the latest 20 PR runs and says so only when that limit is reached.

Enrollment is an explicit work request. It does not claim repository readiness,
preview stages or execute devkit. Both new activity kinds use Draft PRs; an existing
PR retains its actual Draft state under the ordinary PR contract.

## 3. States

- **populated**: enroll the named PR or open its existing Run.
- **loading**: history names the pending lookup; enrollment disables duplicate submission. The selected document remains available.
- **empty**: no PR runs for this unit is distinct from failed lookup, and unit status is omitted. A proposal points to Start Planning or Development and enrollment; a spec points to enrollment. Enrollment requires a positive integer PR number; blank, zero and fractional values keep submission disabled.
- **error**: history shows a plain alert and offers Retry history without clearing the document. Enrollment outcomes appear below the enrollment form; uncertain exact-request recovery remains in the workspace region above both viewer modes.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Enroll PR | `UC-complete-sdd-workflow` 1 | populated | loading | | `CAP-SDD-native-delivery` | Ordinary PR registration outcome appears. |
| Open run | `UC-complete-sdd-workflow` 1 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact Run opens, at its Decisions section when the run is paused or blocked. |
| Open decisions (unit status) | `UC-complete-sdd-workflow` 1 | populated | populated | `UX-run-page` | `CAP-PR-operator-decisions` | The owed run opens at its Decisions section. |
| Select unit / Browse repository | `UC-inspect-repository-documents` 5, `UC-inspect-repository-documents` 6 | empty, populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Selected branch document remains visible. |
| Retry history | global: read retained unit executions | populated, error | loading | | `CAP-SDD-native-delivery` | Stored Run links refresh without evaluation. |
