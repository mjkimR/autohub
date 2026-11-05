---
id: UX-connection-test-check
title: Connection and CI Check
summary: "Run a read-only project GitHub and CI access check against a representative PR and inspect its saved readiness report."
area: projects
element: modal
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-connection-test-check] Connection and CI Check

## 1. Purpose

- **Primary task**: check read-only Project connection readiness.
- **Facts to commit**: project, repository, representative PR number and the distinction from an AI execution test.
- **Secondary items**: PR verification details and its external GitHub link follow the overall result.

## 2. Content

The project identity and PR-number/Run Check controls precede the saved report. The overall readiness result is primary within that report; individual verification items explain it.

- Project connection (check subject): name, repository and editable positive PR number.
- Project connection (access report): overall ready/incomplete status, check time and named passed/failed/skipped items.
  - Project connection (representative PR observation): PR number, head SHA, verification status/reason and GitHub link when available.
- Close action: returns to the originating screen or panel.

## 3. States

- **populated**: the saved result is displayed when available; run another check or close.
- **empty**: no saved result; choose a representative PR and run the check.
- **loading**: `Checking...` disables check inputs and duplicate requests.
- **error**: request failures produce a toast; reported incomplete readiness remains a visible result, not a request exception.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Run Check | `UC-configure-project-connection` 5 | populated, empty | loading |  | `CAP-PROJ-project-connections` | Checking indicator appears; the report is replaced by the returned result. |
| Read readiness and verification items | `UC-configure-project-connection` 6, `UC-configure-project-connection` 6a | populated | populated |  | `CAP-PROJ-project-connections` | The result distinguishes ready from incomplete/failed, with success or warning toast. |
| Check fails after project changes | `UC-configure-project-connection` 6b | loading | error |  | `CAP-PROJ-project-connections` | A request error is shown; no newer saved revision is claimed verified. |
| Close / dismiss | global: return to the originating connection view | populated, empty, error | populated | close |  | The report can be reopened from the parent. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectConnectionCheckDialog.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
