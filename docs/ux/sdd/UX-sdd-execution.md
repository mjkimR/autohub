---
id: UX-sdd-execution
title: Enroll repository activity work
summary: "The execution panel enrolls an existing activity PR with descriptive unit intent and opens retained runs without a runtime or workflow preflight."
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

- **Primary task**: enroll or inspect an existing unit PR.
- **Facts to commit**: unit path, PR number and optional effort/catalog.
- **Secondary items**: retained Run links appear below the enrollment control.

## 2. Content

- SDD unit (selected directory and branch).
- PR run (existing PR number, preferences, enroll action and retained Run/PR links).

Enrollment is an explicit work request. It does not claim repository readiness,
preview stages or execute devkit. Both new activity kinds use Draft PRs; an existing
PR retains its actual Draft state under the ordinary PR contract.

## 3. States

- **populated**: enroll the named PR or open its existing Run.
- **loading**: enrollment/history is pending and duplicate submission is disabled.
- **empty**: select a unit or supply an existing PR number.
- **error**: show the exact request failure and offer retry without inventing an owner.
- **retired**: legacy Run links remain inspectable; no native resume is offered.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Enroll selected PR | `UC-complete-sdd-workflow` 1 | populated | loading | | `CAP-SDD-native-delivery` | Ordinary PR registration outcome appears. |
| Open run | `UC-complete-sdd-workflow` 1 | populated, retired | populated | `UX-run-page` | `CAP-SDD-native-delivery` | The exact Run opens. |
| Select unit / Browse repository | `UC-inspect-repository-documents` 5, `UC-inspect-repository-documents` 6 | empty, populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Selected branch document remains visible. |
| Refresh history | global: read retained unit executions | populated, retired, error | loading | | `CAP-SDD-native-delivery` | Stored Run links refresh without evaluation. |
