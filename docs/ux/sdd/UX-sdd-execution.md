---
id: UX-sdd-execution
title: Enroll repository activity work
summary: "The selected SDD unit shows execution history and a secondary existing-PR enrollment disclosure with an initially empty PR number."
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

- **Primary task**: inspect executions for the selected SDD unit.
- **Facts to commit**: unit path, exact Run/PR; enrollment additionally requires an explicitly entered positive integer PR number and effort.
- **Secondary items**: Enroll an existing PR is a collapsed disclosure inside the unit work panel. Its button is labeled Enroll PR.

## 2. Content

- SDD unit (selected directory and document branch; changing unit/branch resets the enrollment form).
- PR run (execution-history rows, independent loading/empty/error state, exact Run/PR links).
- PR run (secondary enrollment disclosure, empty Pull request field, activity effort and Enroll PR).

Enrollment is an explicit work request. It does not claim repository readiness,
preview stages or execute devkit. Both new activity kinds use Draft PRs; an existing
PR retains its actual Draft state under the ordinary PR contract.

## 3. States

- **populated**: enroll the named PR or open its existing Run.
- **loading**: history names the pending lookup; enrollment disables duplicate submission. The selected document remains available.
- **empty**: no executions found is distinct from failed lookup. Enrollment requires a positive integer PR number; blank, zero and fractional values keep submission disabled.
- **error**: history offers Retry history without clearing the document. Enrollment outcomes and uncertain exact-request recovery remain in the workspace region above both viewer modes.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Enroll PR | `UC-complete-sdd-workflow` 1 | populated | loading | | `CAP-SDD-native-delivery` | Ordinary PR registration outcome appears. |
| Open run | `UC-complete-sdd-workflow` 1 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact Run opens. |
| Select unit / Browse repository | `UC-inspect-repository-documents` 5, `UC-inspect-repository-documents` 6 | empty, populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Selected branch document remains visible. |
| Retry history | global: read retained unit executions | populated, error | loading | | `CAP-SDD-native-delivery` | Stored Run links refresh without evaluation. |
