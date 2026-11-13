---
id: UX-pipeline-runs
title: Pipeline Runs
summary: "The Pipeline Runs screen lists PR run state, ownership and recovery controls and opens enrollment, decision and attempt-history dialogs."
area: delivery
element: screen
status: active
usecases:
  - UC-deliver-pull-request
  - UC-complete-sdd-workflow
capabilities:
  - CAP-PR-pull-request-delivery
  - CAP-PR-operator-decisions
  - CAP-SDD-workflow-control
---

# [UX-pipeline-runs] Pipeline Runs

## 1. Purpose

- **Primary task**: Inspect and control a PR run.
- **Facts to commit**: Project connection, PR identity, run state/revision, wait reason and lease status.
- **Secondary items**: Enrollment, decisions, PR attachment and execution-attempt history open dedicated modals.

## 2. Content

The PR run list is the primary region. Filters stay above it; row actions belong
to their PR run. The dashboard's Needs-you tile in `UX-dashboard` opens this screen
with default filters. The same view can be scoped to one Project connection in its
detail screen. The route `/projects/runs` also accepts a run deep link.

- Project connection (project filter; fixed in a scoped view).
- PR run (searchable and paginated row): PR number/title, branch, state, revision,
  wait reason, lease holder/expiry and creation time. The state is the PR run state
  badge: a label plus a decorative icon, ranked as failure (failed), attention
  (paused, blocked), quiet progress (dispatching, implementing), quiet success
  (completed) or neutral (queued, awaiting CI, canceled), per
  `docs/steering/visual-style.md`. The pause reason stays below the badge. Row
  controls such as Pause Run and Resume Run are ink with no status hue.
  - `UX-run-decisions` (modal; opened for an inspected row).
  - `UX-attempt-history` (modal; opened for the row's Execution attempts).
  - `UX-attach-pull-request` (modal; offered only when no PR number is attached).
- `UX-enroll-pull-request` (modal; opened by Enroll PR).

State, group and text filters reload the first page. A linked run can select its
project and open decisions or attempts. Ordinary PR readiness is changed in
GitHub, not by a ready toggle on this screen.

## 3. States

- **populated**: Rows show the last loaded PR run state; refresh or inspect a row before acting.
- **empty**: No rows match; change filters, refresh or enroll a PR.
- **loading**: The table announces loading; wait for the requested page.
- **error**: The list is unavailable and exposes retry; failed actions show a toast.
- **operating**: The affected row disables mutation controls and keeps its state badge until its request settles and the refreshed state arrives; inspect the resulting state afterward.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Enroll PR | `UC-deliver-pull-request` 1 | populated | populated | `UX-enroll-pull-request` | `CAP-PR-pull-request-delivery` | Enrollment dialog opens. |
| Refresh / Advance Run | `UC-deliver-pull-request` 4, `UC-complete-sdd-workflow` 7 | populated | loading |  | `CAP-PR-pull-request-delivery` | Loading state or action toast precedes the refreshed run state. |
| View Attempt History | `UC-deliver-pull-request` 4 | populated | populated | `UX-attempt-history` | `CAP-PR-pull-request-delivery` | The selected run’s attempt dialog opens. |
| Decisions | global: inspect the selected run before choosing a task | populated | populated | `UX-run-decisions` | `CAP-PR-operator-decisions` | Current question and native workflow context load. |
| Attach Pull Request | global: associate a PR with eligible work that has no PR number | populated | populated | `UX-attach-pull-request` | `CAP-PR-pull-request-delivery` | Attachment dialog opens. |
| Pause Run | `UC-deliver-pull-request` *a, `UC-complete-sdd-workflow` *a | populated | operating |  | `CAP-PR-pull-request-delivery` | Success toast and refreshed stopped state. |
| Resume Run | `UC-deliver-pull-request` *c | populated | operating |  | `CAP-PR-pull-request-delivery` | A blocked-run reason is confirmed when present; the resumed state or refusal is shown. |
| Cancel Run | `UC-deliver-pull-request` *b | populated | operating |  | `CAP-PR-pull-request-delivery` | Browser confirmation precedes cancellation; the refreshed row shows the outcome. |
| Open on GitHub | global: open GitHub for PR review and readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | The PR opens in a separate tab for external readiness/review. |
| Navigate to Projects | global: leave execution inspection through the application navigation | populated | populated | `UX-projects` |  | Project connections are shown. |

## 5. Evidence

- [PipelineRunsView.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunsView.svelte).
- [PipelineRunRow.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunRow.svelte).
- [RunStateBadge.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunStateBadge.svelte) and [presentation.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.ts), with [presentation.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.test.ts) covering every run state.
- [PipelineRunsView.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunsView.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
