---
id: UX-enroll-pull-request
title: Enroll Pull Request
summary: "The enrollment dialog binds an existing pull request to a Project connection and optional AI catalog, including descriptive unit intent for SDD projects."
area: delivery
element: modal
status: active
usecases:
  - UC-deliver-pull-request
capabilities:
  - CAP-PR-pull-request-delivery
  - CAP-SDD-native-delivery
---

# [UX-enroll-pull-request] Enroll Pull Request

## 1. Purpose

- **Primary task**: Enroll an existing PR for delivery.
- **Facts to commit**: Selected Project connection, positive PR number, AI catalog selection and whether work is already implemented.
- **Secondary items**: Cancel returns to the PR run list without submitting.

## 2. Content

The enrollment form is the primary region. Project connection selection governs
whether the SDD unit intent field appears.

- Project connection (required selector).
- PR run (candidate PR number and Already implemented flag).
- AI catalog (enabled pipeline-delivery options or Project default).
- SDD unit (requested unit directory; only for an SDD Project connection).
- Submit/Cancel controls (below the fields).

## 3. States

- **populated**: Editable form; select a project and valid PR number before enrollment.
- **empty**: No project is selected; select one before submitting.
- **loading**: Enrolling disables repeat submission; wait or inspect the resulting toast.
- **error**: A failed enrollment displays an error toast; correct input or inspect the existing PR run before retrying.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Enroll PR | `UC-deliver-pull-request` 1 | populated | loading | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | Success closes the dialog, reports the enrolled PR and reloads runs; refusal keeps the form open. |
| Cancel / close | global: dismiss enrollment without creating a PR run | populated | populated | close |  | The parent list remains visible. |

## 5. Evidence

- [EnrollPullRequestDialog.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/EnrollPullRequestDialog.svelte).

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
