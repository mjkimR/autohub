---
id: UX-run-page
title: PR Run Page
summary: "The PR run page shows one state-driven next action, retained origin links, decisions, attempts and ended-run recovery using returned Work Item IDs without owner scans."
area: delivery
element: screen
status: active
usecases:
  - UC-deliver-pull-request
  - UC-resolve-run-question
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
  - UC-start-sdd-activity
capabilities:
  - CAP-PR-pull-request-delivery
  - CAP-PR-operator-decisions
  - CAP-SDD-native-delivery
  - CAP-WORK-work-plan-execution
---

# [UX-run-page] PR Run Page

## 1. Purpose

- **Primary task**: Take the next action a PR run needs, or confirm that it needs none.
- **Facts to commit**: PR run state, the decision waiting on the operator, wait reason, PR identity, branch, lease
  and revision.
- **Secondary items**: Decisions and Execution attempts are sections below the header; enrollment, PR attachment and
  Work Item recovery live in `UX-enroll-pull-request`, `UX-attach-pull-request` and `UX-work-plans`.

## 2. Content

The route is `/projects/{projectId}/runs/{runId}`. `/runs/{runId}` resolves the project from the run and replaces
itself with that route, keeping its section anchor. The old list links `/projects/runs?run={id}[&view=decisions]`
and `/projects/{projectId}?tab=runs&run={id}` redirect here; `view=decisions` lands on the Decisions section. A run
opened under another project's path redirects to its own project.

The header and its action row are primary. Sections follow in this order: the next step of an ended run, Related origins, Decisions, Execution attempts. Section anchors are `#next-step`, `#decisions` and `#attempts`.

- PR run (breadcrumb): Projects › Project connection › Runs › PR number.
- PR run (header): state badge, decision-wait marker when a decision is pending, SDD badge for SDD runs, PR title,
  PR link, branch, lease holder and expiry, last update with revision, wait reason, run identifier, creation time and
  next scheduled check.
- PR run (action row): one state-driven primary action, then the secondary actions that apply.
  - Primary action, in priority order: Answer question (open Run question), Resume with saved answer (answered
    question not yet applied), Inspect retired evidence (legacy SDD history), Check decision (answer application
    pending), Next step (failed run), Resume (paused or blocked run whose decisions are known and none holds it),
    Attach PR (active run without a PR). Decision actions move to the Decisions section; a run held by a pending
    decision never offers a plain Resume. When the run's decisions are unknown (the read failed or was incomplete)
    no primary action is shown on the page (Open run is the page itself) and Resume is only a secondary action.
  - Secondary actions: Resume (when not primary and allowed), Pause (active run), Advance now (re-evaluates the run
    instead of waiting for its next scheduled check; non-terminal run), Attach PR, Inspect PR, Cancel run
    (non-terminal run; confirmed). Refresh reloads the run, its decision status and attempts; it keeps the
    Decisions section mounted (draft answer and notices stay), which has its own Refresh decisions.
- PR run (next step; failed or canceled run): states that the run cannot be resumed and that its record is kept.
  - Work Item (owning item; when a Work Plan item names this run): item and Work Plan IDs from the Run read, with Open Work
    Item recovery to that item in `UX-work-plans` and Review attempt errors.
  - Replacement guidance (when no Work Item names this run): Enroll PR opens the project's Runs tab
    (`UX-pipeline-runs`) and Work Plans opens the Plans tab.
- PR run (Related origin): the proven category or Origin unknown, followed by retained Work Plan/Work Item links, current SDD unit, related claim history/batch links and exact external Provider session URLs. Missing session URLs remain ID text; category evidence can be known without an available subject link.
- SDD unit links include the Run branch and open that unit in `UX-repository`; related history is labeled separately from the current unit.
- `UX-run-decisions` (Decisions section; the run's wait reason stays in the header).
- `UX-attempt-history` (Execution attempts section).

Visual roles follow `docs/steering/visual-style.md`: the decision-wait marker is the attention Badge; actions are
ink; Cancel run is the quiet destructive variant.

## 3. States

- **loading**: a status line announces the run load; wait for the header.
- **populated**: the header, actions and sections show the last consistent run read; act on the primary action or
  a secondary one.
- **not-found**: the run does not exist or its history expired; Back to project runs returns to the project's run
  list.
- **error**: without loaded data the page offers Retry and Back to project runs; after a failed refresh an alert
  keeps the last loaded run visible and offers Retry.
- **operating**: a header action disables the action row until it settles; success reloads the run and its
  sections, failure shows a toast.
- **ended**: a failed or canceled run shows its next step; history stays readable.
- **empty sections**: Decisions shows "No questions or SDD activity yet."; Execution attempts shows that no attempt
  is recorded yet.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Answer question | `UC-resolve-run-question` 2 | populated | populated |  | `CAP-PR-operator-decisions` | The page moves to the Decisions section and its answer editor. |
| Resume with saved answer | `UC-resolve-run-question` 4 | populated | populated |  | `CAP-PR-operator-decisions` | The page moves to the saved answer in Decisions, where the answer is selected explicitly. |
| Inspect retained native evidence | `UC-decide-sdd-proposal` 1 | populated | populated | `UX-sdd-run` | `CAP-SDD-native-delivery` | Read-only retired evidence opens without authority. |
| Next step | `UC-deliver-pull-request` *d | ended | ended |  | `CAP-PR-pull-request-delivery` | The page moves to the next-step section. |
| Open Work Item recovery | `UC-deliver-pull-request` *d | ended | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | The Plans tab opens with the owning Work Item expanded. |
| Enroll PR / Work Plans | global: register replacement work for an ended run that no Work Item owns | ended | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | The project's Runs or Plans tab opens. |
| Resume | `UC-deliver-pull-request` *c | populated | operating |  | `CAP-PR-pull-request-delivery` | A blocked-run reason is confirmed when present; the resumed state or refusal is shown. |
| Pause | `UC-deliver-pull-request` *a | populated | operating |  | `CAP-PR-pull-request-delivery` | A toast confirms the pause and the stopped state loads. |
| Advance now | `UC-deliver-pull-request` 4 | populated | operating |  | `CAP-PR-pull-request-delivery` | A toast names the resulting state. |
| Attach PR | global: associate a PR with eligible work that has no PR number | populated | populated | `UX-attach-pull-request` | `CAP-PR-pull-request-delivery` | The attachment dialog opens; success reloads the run. |
| Cancel run | `UC-deliver-pull-request` *b | populated | operating |  | `CAP-PR-pull-request-delivery` | Confirmation precedes cancellation; the ended state and next step load. |
| Inspect PR | global: open GitHub for PR review and readiness outside Hub | populated | populated | end | `CAP-PR-pull-request-delivery` | The PR opens in a separate tab. |
| Refresh / Retry | `UC-complete-sdd-workflow` 1, `UC-complete-sdd-workflow` 2, `UC-complete-sdd-workflow` 3, `UC-complete-sdd-workflow` 7, `UC-start-sdd-activity` 5 | populated, error | loading |  | `CAP-PR-pull-request-delivery` | The run, its pending decisions and its attempts reload; the Decisions section keeps its draft and notices; a failure keeps the last data. |
| SDD unit / batch origin | `UC-deliver-pull-request` 4 | populated, ended | populated | `UX-repository` | `CAP-PR-pull-request-delivery` | The exact named unit/branch or retained batch opens, or its unavailable explanation appears. |
| Work Plan / Work Item origin | `UC-deliver-pull-request` 4 | populated, ended | populated | `UX-work-plans` | `CAP-PR-pull-request-delivery` | The existing exact object anchor opens. |
| Provider session origin | global: inspect retained external evidence | populated, ended | populated | end | `CAP-PR-pull-request-delivery` | The retained external URL opens separately; absent URLs remain text. |
| Breadcrumb Projects / project / Runs | global: navigate up from the run | populated, not-found, error | populated | `UX-pipeline-runs` |  | Projects, the project or its run list opens. |
| Back to project runs | global: leave a missing run | not-found | populated | `UX-pipeline-runs` |  | The project's run list opens. |

## 5. Evidence

- [RunPageView.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunPageView.svelte),
  [RunHeader.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunHeader.svelte),
  [RunNextStep.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunNextStep.svelte),
  [RunRedirect.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunRedirect.svelte)
  and [RunActions.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunActions.svelte).
- [run-actions.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-actions.ts) maps
  state and pending decisions to the primary action; [run-links.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-links.ts)
  builds run URLs and old-link redirects.
- [RunPageView.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunPageView.integration.test.ts)
  and [run-actions.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-actions.test.ts);
  test assertions were inspected and run with `just test-ui`.

The page reads pending decisions from the Decision inbox list (up to five pages of 100 for the project); the run
record supplies its retained Work Item/Plan IDs, so recovery sends no Work Plan list scan. This
description does not claim a live provider result. `RunOrigins.integration.test.ts` and `RunPageView.integration.test.ts` enforce exact links, unknown/missing URL states and recovery without owner scans.
