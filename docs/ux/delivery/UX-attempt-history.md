---
id: UX-attempt-history
title: Execution Attempts
summary: "The execution-attempt dialog presents immutable attempt summaries, correlation identities and expandable request/reply timelines for one PR run."
area: delivery
element: modal
status: active
usecases:
  - UC-deliver-pull-request
capabilities:
  - CAP-PR-pull-request-delivery
---

# [UX-attempt-history] Execution Attempts

## 1. Purpose

- **Primary task**: Inspect an Execution attempt and its delivered requests/replies.
- **Facts to commit**: PR run identity, branch, wait reason and recorded attempt outcomes.
- **Secondary items**: Provider conversation links open externally; Close returns to the PR run list.

## 2. Content

The attempt list is primary. The PR run context and aggregate request/elapsed
summary precede it; request/reply timelines expand within their Execution attempt.

- PR run (header identity, state, branch and wait reason).
- Execution attempt (number, kind, state, idempotency key, request digest, times
  and optional failure detail).
  - Execution attempt (chronological request/reply timeline; loaded when opened).
  - Execution attempt (external conversation link when recorded).

## 3. States

- **populated**: Inspect attempts or expand their request/reply timelines.
- **empty**: No attempts are recorded; close or reload through the parent after work advances.
- **loading**: Attempts or a timeline announce loading; wait for the result.
- **error**: Attempt-list failure offers retry; a failed request/reply timeline explains the failure and can be reopened by closing and opening the dialog.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Show requests and replies | `UC-deliver-pull-request` 4 | populated | loading |  | `CAP-PR-pull-request-delivery` | The attempt’s chronology, explicit empty state or load error appears. |
| Retry attempts | global: reload an unavailable immutable-attempt list | error | loading |  | `CAP-PR-pull-request-delivery` | The list and summary are fetched again. |
| Close | global: return from history to the run list | populated | populated | close |  | The parent list remains visible. |

## 5. Evidence

- [AttemptHistoryDialog.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttemptHistoryDialog.svelte).
- [AttemptTimeline.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttemptTimeline.svelte).

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
