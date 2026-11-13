---
id: UX-pipeline-runs
title: PR Runs
summary: "The PR runs screen lists PR run state, ownership and pending decisions with one state-driven action per row, and opens each run's page and the enrollment dialog."
area: delivery
element: screen
status: active
usecases:
  - UC-deliver-pull-request
  - UC-complete-sdd-workflow
capabilities:
  - CAP-PR-pull-request-delivery
  - CAP-PR-operator-decisions
---

# [UX-pipeline-runs] PR Runs

## 1. Purpose

- **Primary task**: Find the PR run that needs attention and take its next action.
- **Facts to commit**: Project connection, PR identity, run state/revision, pending decision, wait reason and lease status.
- **Secondary items**: Each run's decisions, attempts and full controls live on `UX-run-page`; enrollment and PR
  attachment open dedicated modals.

## 2. Content

The PR run list is the primary region. Filters stay above it; row actions belong
to their PR run. The empty state of `UX-attention` links here with default filters. The same view can be scoped to one Project connection in its
detail screen. The page title is "PR runs" (glossary term).

- Project connection (project filter; fixed in a scoped view).
- PR run (searchable and paginated row): PR number/title, branch, state, revision,
  wait reason, lease holder/expiry and creation time. The PR title opens `UX-run-page`.
  The state is the PR run state badge: a label plus a decorative icon, ranked as
  failure (failed), attention (paused, blocked), quiet progress (dispatching,
  implementing), quiet success (completed) or neutral (queued, awaiting CI,
  canceled), per `docs/steering/visual-style.md`. The pause reason stays below the badge.
  - Decision-wait marker (attention Badge beside the state; when the Decision inbox
    lists a pending decision for the run): Question waiting, Answer saved — resume
    pending, or Approval waiting.
  - Primary action (one per row, state-driven, same rule as `UX-run-page`): Answer
    question, Resume with saved answer, Review approval or Check decision link to the
    run page's Decisions section; Next step links to a failed run's next step; Resume
    acts on a stopped run whose decisions are known and none holds it; Attach PR opens
    `UX-attach-pull-request`; otherwise Open run. A stopped run whose decisions are
    unknown gets Open run, and plain Resume stays in the overflow menu. Each primary
    action's accessible name contains its visible label and names the PR (for example
    "Apply answer (resume with saved answer) for PR #7").
  - More actions (overflow menu): Open run, Decisions, Attempts & errors, Resume (only
    when allowed), Pause, Advance now, Attach PR, Inspect PR and Cancel run, each when
    it applies. Controls are ink with no status hue; Cancel run is the destructive item.
- `UX-enroll-pull-request` (modal; opened by Enroll PR).

Pending decisions come from one Decision inbox read of up to 100 entries for the
filtered project, not one request per row. It reloads only on first load, when the
project filter changes, on Refresh and after an operation; search and state filters
reuse it, and a response overtaken by a newer read or a project change is dropped.
When that read fails or is incomplete, rows without an entry treat their decisions as
unknown: the primary action is Open run and Resume is only in the overflow menu.

The old run deep links `/projects/runs?run={id}[&view=decisions]` and
`/projects/{projectId}?tab=runs&run={id}` redirect to `UX-run-page` instead of
loading the list. Ordinary PR readiness is changed in GitHub, not by a ready toggle
on this screen.

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
| Refresh | `UC-deliver-pull-request` 4 | populated | loading |  | `CAP-PR-pull-request-delivery` | The list and its pending decisions reload. |
| Open run (PR title, primary action or menu) | `UC-deliver-pull-request` 4, `UC-complete-sdd-workflow` 7 | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run's page opens. |
| Answer question / Resume with saved answer | global: open the run page section that holds the run's owed question | populated | populated | `UX-run-page` | `CAP-PR-operator-decisions` | The run page opens at its Decisions section. |
| Next step | global: open a failed run's recovery path on its page | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The failed run's page opens at its next step. |
| Attempts & errors | `UC-deliver-pull-request` 4 | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run page opens at its Execution attempts section. |
| Attach PR | global: associate a PR with eligible work that has no PR number | populated | populated | `UX-attach-pull-request` | `CAP-PR-pull-request-delivery` | Attachment dialog opens. |
| Advance now | `UC-deliver-pull-request` 4, `UC-complete-sdd-workflow` 7 | populated | operating |  | `CAP-PR-pull-request-delivery` | A toast names the resulting state and the list reloads. |
| Pause | `UC-deliver-pull-request` *a | populated | operating |  | `CAP-PR-pull-request-delivery` | Success toast and refreshed stopped state. |
| Resume | `UC-deliver-pull-request` *c | populated | operating |  | `CAP-PR-pull-request-delivery` | A blocked-run reason is confirmed when present; the resumed state or refusal is shown. Not offered while a decision holds the run; in the overflow menu when the run's decisions are unknown. |
| Cancel run | `UC-deliver-pull-request` *b | populated | operating |  | `CAP-PR-pull-request-delivery` | Browser confirmation precedes cancellation; the refreshed row shows the outcome. |
| Inspect PR / Open on GitHub | global: open GitHub for PR review and readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | The PR opens in a separate tab for external readiness/review. |
| Navigate to Projects | global: leave execution inspection through the application navigation | populated | populated | `UX-projects` |  | Project connections are shown. |

## 5. Evidence

- [PipelineRunsView.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunsView.svelte).
- [PipelineRunRow.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunRow.svelte) and [RunActions.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunActions.svelte).
- [RunStateBadge.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunStateBadge.svelte) and [presentation.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.ts), with [presentation.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.test.ts) covering every run state.
- [PipelineRunsView.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunsView.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
