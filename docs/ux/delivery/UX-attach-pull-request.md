---
id: UX-attach-pull-request
title: Attach Pull Request
summary: "The attachment dialog associates a PR number and optional URL with an eligible PR run that has no attached pull request."
area: delivery
element: modal
status: active
usecases: []
capabilities:
  - CAP-PR-pull-request-delivery
---

# [UX-attach-pull-request] Attach Pull Request

## 1. Purpose

- **Primary task**: Attach a PR to an existing eligible PR run.
- **Facts to commit**: The selected run identity, PR number and optional PR URL.
- **Secondary items**: Cancel returns to the unchanged run list.

## 2. Content

The PR association fields are primary; the selected PR run remains named in the
header so attachment is not confused with creating another execution.

- PR run (selected association owner).
- PR run (editable PR number and optional GitHub URL).
- Attach PR and Cancel controls.

## 3. States

- **populated**: Association fields are editable; submit when the PR identity is correct.
- **loading**: Attaching disables repeat submission; wait for the response.
- **error**: A refusal/error toast leaves the form open for inspection or correction.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Attach PR | global: attach an existing PR to eligible execution work | populated | loading | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | Success closes the dialog and reloads the run list; an error preserves the form. |
| Cancel / close | global: leave attachment without modifying the association | populated | populated | close |  | Dialog closes. |

## 5. Evidence

- [AttachPullRequestDialog.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttachPullRequestDialog.svelte).

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
