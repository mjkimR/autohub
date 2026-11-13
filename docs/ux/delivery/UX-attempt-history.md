---
id: UX-attempt-history
title: Execution Attempts
summary: "The Execution attempts panel of the PR run page presents immutable attempt summaries, correlation identities and expandable request/reply timelines for one PR run."
area: delivery
element: panel
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
- **Secondary items**: Provider conversation links open externally; the panel is the Execution attempts section (`#attempts`) of `UX-run-page`, which owns the run header and navigation.

## 2. Content

The attempt list is primary. The aggregate request/elapsed summary precedes it; request/reply timelines expand within their Execution attempt.

- Execution attempt (number, kind, state, idempotency key, request digest, times
  and optional failure detail).
  - Execution attempt (chronological request/reply timeline; loaded when opened).
  - Execution attempt (external conversation link when recorded).

## 3. States

- **populated**: Inspect attempts or expand their request/reply timelines.
- **empty**: No attempts are recorded; Refresh the run page after work advances.
- **loading**: Attempts or a timeline announce loading; wait for the result.
- **error**: Attempt-list failure offers retry; a failed request/reply timeline explains the failure and can be reopened by hiding and showing it.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Show requests and replies | `UC-deliver-pull-request` 4 | populated | loading |  | `CAP-PR-pull-request-delivery` | The attempt’s chronology, explicit empty state or load error appears. |
| Retry attempts | global: reload an unavailable immutable-attempt list | error | loading |  | `CAP-PR-pull-request-delivery` | The list and summary are fetched again. |
| Run page navigation | global: leave the attempts section through the run page breadcrumb | populated | populated | `UX-run-page` |  | The run page header and breadcrumb stay available above the section. |

## 5. Evidence

- [RunAttempts.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunAttempts.svelte).
- [AttemptTimeline.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttemptTimeline.svelte).

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
