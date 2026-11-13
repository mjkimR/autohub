---
id: CAP-PR-pull-request-delivery
title: Pull Request Delivery
summary: "PR Runs own implementation, current-head CI and policy-controlled merging. Guarded Work Item recovery retains terminal Run identity and budgets while ordinary paused/blocked resume keeps its existing meaning."
area: delivery
status: active
usecases:
  - UC-deliver-pull-request
  - UC-complete-sdd-workflow
  - UC-execute-work-plan
entrypoints:
  - modules/hub/app/features/project_management/projects/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/lifecycle.py
---

# [CAP-PR-pull-request-delivery] Pull Request Delivery

## 1. Summary

One `PipelineRun` follows one repository PR through implementation, verification
and merge or an explicit stop. GitHub owns PR contents, CI and merge facts; Hub
owns dispatch identity, observations, retries and the permission to continue.
`UC-deliver-pull-request` describes direct delivery. `UC-execute-work-plan` uses
the same executor after `CAP-WORK-work-plan-execution` prepares an Item's PR.

## 2. Scope & Boundary

- **In-Scope**: direct PR enrollment, immutable attempts, recoverable mention
  delivery, observation, automatic CI/conflict repair, final merge checks and
  pause/resume/cancel of ordinary PR runs.
- **Out-of-Scope**: Work Plan registration and dependency release belong to
  `CAP-WORK-work-plan-execution`; repository checks run in GitHub Actions;
  provider implementation occurs outside Hub. `CAP-PR-ci-observation` owns exact
  workflow/job evidence; `CAP-PR-agent-dispatch` owns mention rendering, delivery
  reconciliation and provider watchdogs. `CAP-PR-operator-decisions` owns Run
  clarification; `CAP-SDD-native-delivery` owns descriptive activity intent and retired native history;
  `CAP-SDK-task-flow-execution` owns SDK flow approval.
- **Scope Excluded**: per-commit human review, remote-provider cancellation,
  exactly-once effects across Hub and GitHub, and automatic creation of a PR by
  the direct enrollment endpoint.

## 3. Business Rules & Policies

1. **Enrollment eligibility**: IF a direct enrollment targets a closed PR, a fork PR or task text containing a prohibited `@codex` mention, THEN Hub MUST reject it with HTTP 422 without creating a Run. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestPullRequestEnrollment.test_unsafe_pull_requests_are_rejected_without_creating_a_run`.
2. **One active owner**: WHILE a PR has a Run in `queued`, `dispatching`, `implementing`, `awaiting_ci`, `paused` or `blocked` for the same project, Hub MUST reject another enrollment with HTTP 409. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestPullRequestEnrollment.test_different_pull_requests_can_enroll_but_duplicate_pull_is_blocked_before_reading_github`.
3. **Read-only enrollment**: WHEN a direct PR enrollment succeeds, Hub MUST retain the PR and recognized linked-Issue snapshot without issuing a GitHub mutation. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestPullRequestEnrollment.test_enrolls_an_open_pull_request_with_its_linked_issues` and its GET-only GitHub fixture.
4. **Existing implementation**: WHERE direct enrollment specifies `implemented=true`, Hub MUST start in `awaiting_ci` with an externally implemented attempt and no implementation delivery. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestPullRequestEnrollment.test_enrolls_an_implemented_pull_request_straight_into_ci_observation`.
5. **Explicit catalog**: WHEN a catalog designation is supplied, Hub MUST choose its exact key or, if no key exists, the unique enabled catalog of the named kind before the project default. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestCatalogDesignation.test_a_designated_key_is_used_and_remembered` and `test_a_kind_resolves_when_exactly_one_enabled_catalog_has_it`.
6. **Catalog refusal**: IF an explicit catalog is ambiguous, missing, disabled or cannot deliver PR work, THEN Hub MUST reject enrollment with HTTP 422 instead of silently substituting another catalog. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestCatalogDesignation.test_an_ambiguous_kind_is_refused`, `test_catalogs_that_cannot_take_the_work_are_refused` and `test_a_disabled_catalog_is_refused_by_key`.
7. **Draft approval**: WHILE a direct PR is Draft, Hub MUST withhold merging regardless of reported mergeability or missing, skipped or successful CI. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_draft_waits_for_ready_approval_then_required_ci` and `test_returning_to_draft_during_merge_recheck_revokes_approval`.
8. **Merge policy**: WHERE `auto_merge=false`, WHEN CI passes, Hub MUST pause the Run instead of merging it. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_ready_approval_does_not_override_disabled_auto_merge`.
9. **Code repair while Draft**: WHERE automatic CI repair is enabled, WHEN an identified code job fails on a Draft PR and its current-epoch repair allowance remains, Hub MUST allow a CI-fix attempt without treating Draft as merge approval. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_draft_still_allows_failed_ci_to_be_fixed`.
10. **Conflict classification**: WHERE automatic merge and conflict repair are enabled, WHEN current-head CI passes and GitHub reports `dirty` or `behind` while the current-epoch conflict-fix allowance remains, Hub MUST request a conflict fix rather than merge that PR. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_a_branch_that_conflicts_with_or_trails_its_base_goes_to_the_agent`.
11. **Repository-rule wait**: IF GitHub refuses merging for a repository rule rather than a confirmed branch conflict, THEN Hub MUST retain an `awaiting_ci` wait without creating a conflict-fix attempt. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_a_refused_merge_is_a_conflict_only_when_github_says_so`.
12. **Final authorization fence**: IF pause, cancellation, project change, lease replacement or active-attempt change invalidates observation before final merge authorization, THEN Hub MUST refuse that stale continuation without sending the merge request. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_ci_observation_rejects_changes_before_merge` and `test_cancel_after_final_ci_read_prevents_merge`.
13. **Concurrent result fence**: IF cancellation commits after an authorized merge request is sent but before its result is recorded, THEN Hub MUST preserve the canceled local state instead of overwriting it with the stale merge result. Check: [`test_merge_stage.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_merge_result_cannot_overwrite_a_concurrent_cancel`.
14. **Resume after a push**: WHEN an ordinary paused Run resumes without an answer and its PR head already moved after the last delivered request, Hub MUST return to CI observation without another implementation delivery. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_resume_after_a_push_watches_ci_without_sending`.
15. **Bounded advancement**: WHEN an advancement invocation reaches its step or time budget, Hub MUST release its lease and leave continuation to a later invocation. Check: [`test_advancement.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_advancement.py), `test_continuation_has_a_step_limit` and `test_deadline_covers_all_steps_and_releases_lease`.
16. **Retained designation**: WHEN a Run resumes while its explicitly designated catalog remains usable, Hub MUST retain that catalog ahead of a changed project selection. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestCatalogDesignation.test_a_resumed_run_keeps_its_designated_catalog_over_the_project_selection`.
17. **Unusable designation fallback**: IF the remembered designated catalog is disabled before resume, THEN Hub MUST use the project catalog while retaining the remembered designation. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestImplementedRunRecovery.test_a_designated_catalog_disabled_later_gives_way_to_the_project_catalog`.
18. **Delivery due time**: WHEN an event or manual advance arrives before a delivery's due time, Hub MUST preserve the delay rather than dispatch it early. Check: [`test_advancement.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_advancement.py), `test_event_refreshes_observation_but_cannot_bypass_delivery_delay`; [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `TestRunRecovery.test_webhook_cannot_deliver_a_quota_retry_early`.
19. **Eligible selection before limit**: WHEN selecting a bounded ready batch, Hub MUST exclude stopped, future-due and actively leased ordinary Runs before applying its selection limit. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_ready_batch_filters_before_limit`.
20. **Dispatch holds do not suppress observation**: WHILE a catalog has a hold, Hub MUST continue selecting otherwise eligible CI-observing Runs rather than treating the hold as a ban on observation. Check: [`test_pipeline_runs_api.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_catalog_hold_gates_only_dispatching_runs`.
21. **Separate tick budgets**: WHEN a project dispatch tick observes existing Runs and admits dispatch candidates, Hub MUST keep the dispatch/follow-up candidates within their separate shared dispatch budget. Check: [`test_task.py`](../../../modules/hub/tests/unit/features/execution/tasks/domains/pipeline/test_task.py), `test_observation_failure_does_not_starve_dispatch`, `test_work_follow_up_uses_remaining_budget_after_existing_runs` and `test_full_dispatch_batch_does_not_expand_for_follow_up`.
22. **No same-tick uncertain resend**: IF delivery fails uncertainly during observation or a catalog hold refuses dispatch, THEN the tick MUST exclude that attempted dispatch from follow-up retries in the same tick. Check: [`test_task.py`](../../../modules/hub/tests/unit/features/execution/tasks/domains/pipeline/test_task.py), `test_uncertain_delivery_after_observation_is_not_retried` and `test_catalog_hold_is_not_retried_in_the_same_tick`.

23. **Guarded terminal recovery**: WHEN an eligible Work Item recovery reactivates a terminal Run, Hub MUST retain the original Run, epoch, attempt numbering and delivery history. Check: `test_terminal_recovery_keeps_run_epoch_and_commits_delivery` in [`test_item_recovery.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_item_recovery.py).
24. **Recovery budget retention**: IF current-epoch repair or retained retry allowance is exhausted, THEN Hub MUST refuse a fresh recovery delivery without resetting any allowance. Check: `test_epoch_budget_exhaustion_never_resets_or_dispatches`. Ordinary subsequent CI-fix attempts keep the per-attempt silent contract; check: [`test_work_item_recovery.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_work_item_recovery.py), `test_review_ordinary_ci_fix_keeps_its_silent_allowance_but_recovery_does_not`.
25. **Recovery owner race**: IF ordinary enrollment wins active ownership while Work Item recovery reconciles, THEN Hub MUST close the losing recovery without dispatching. Check: [`test_work_item_terminal_recovery.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_work_item_terminal_recovery.py), `test_ordinary_enrollment_wins_during_recovery_io_without_loser_dispatch` (PostgreSQL).
26. **Recovery push adoption**: WHEN recovery establishes an already implemented current head, Hub MUST continue CI without repeating implementation. Check: `test_pushed_implementation_advances_ci_without_delivery` in the recovery integration suite.

## 4. Interfaces & Data Contracts

### Public HTTP surface

All paths below are under `/api/v1`. The application authentication boundary
applies before these routes; internal lease/worker endpoints are not MCP tools.

| Method and path | Input and outcome |
| --- | --- |
| `POST /projects/{project_id}/runs` | `pull_number > 0`, optional `catalog`, `implemented=false` by default; HTTP 201 with `PipelineRunRead` |
| `GET /pipeline-runs` | Optional project, state, search, exact PR number and group filters; `offset >= 0`, `limit` 1–100; `items` and `total_count` |
| `GET /pipeline-runs/{run_id}` | Current Run snapshot, state, revision and wait information |
| `GET /pipeline-runs/{run_id}/attempts` | Attempts and aggregate request/time summary |
| `GET /pipeline-runs/{run_id}/attempts/{attempt_id}/deliveries` | Durable delivery identities and publication times |
| `GET /pipeline-runs/{run_id}/attempts/{attempt_id}/replies` | Observed provider replies |
| `POST /pipeline-runs/{run_id}/advance` | One bounded progression invocation |
| `POST /pipeline-runs/{run_id}/pause` | Optional reason; invalidates the observation lease |
| `POST /pipeline-runs/{run_id}/resume` | Required `request_id` and `expected_revision`; optional `answer_id`; only paused/blocked ordinary Runs resume |
| `POST /pipeline-runs/{run_id}/cancel` | Ends local progression; no promise of remote cancellation |

The direct ordinary path starts `queued → dispatching → implementing →
awaiting_ci`. Repairs return through dispatch; successful observed merging reaches
`completed`. `failed` and `canceled` are terminal for ordinary controls; the guarded Work Item recovery entry below is the explicit exception. `paused` and `blocked` require
operator action. GitHub can already have accepted an effect when a later local
authorization check fails.

`PipelineRunRead` includes project/catalog identity, captured project revision,
PR snapshot, branch, `revision`, `epoch`, lease metadata and `next_action_at`.
Attempts retain `request_snapshot`, canonical `request_digest`,
`idempotency_key`, kind and provider correlation. Deliveries belong to attempts;
the exact delivery recovery/marker contract belongs to `CAP-PR-agent-dispatch`.
A deliberate resume without a push can create a new attempt and send new work.

### Work Item recovery owner

`CAP-WORK-work-plan-execution` owns the recovery request and history. Its guarded owner entry accepts only the same linked failed/canceled Run and original owned open PR after reconciliation establishes that prior delivery stopped. It atomically activates that Run with its durable next intent under active-owner uniqueness. Uncertain comment/provider outcomes retain their existing markers and receive read-only reconciliation. Correctly merged original work records success without another delivery.

Recovery never increments `epoch`, resets quota counters or discards attempts. Two CI-fix attempts and one conflict-fix attempt remain the current-epoch bounds. A fresh recovery delivery consumes the retained retry allowance; prior silent/recovery deliveries prevent a fresh recovery request from manufacturing another allowance. The ordinary per-attempt watchdog in `CAP-PR-agent-dispatch` remains unchanged for later CI/fix attempts. Already pushed-head or external-implementation evidence instead enters current-head CI without another implementation request. Ordinary paused/blocked resume retains its existing API and meaning.

### Catalog and advancement selection

Enrollment's `catalog` first matches an exact key; otherwise its lowercased value
must identify exactly one enabled kind. Without a designation, selection uses
the project's `ai_catalog_id`, then the seeded `personal-codex` catalog. Resume
keeps `requested_catalog_id` while it exists, is enabled and supports PR delivery;
otherwise it follows the project selection. A missing explicitly selected
project catalog conflicts rather than guessing a replacement.

Ticks call the common advancement loop with `respect_due=true`. Events/manual
advances may refresh their first implementation/CI observation early but never
bypass a future queued/dispatching delivery. A new CI repair clears the obsolete
observation delay. Selection orders observations before uncertain delivery and
new work. Legacy native authority is permanently retired. Paused Runs do not
auto-resume without their ordinary explicit control.

The project's task uses `MAX_CONCURRENT_TASKS` as its batch/semaphore bound
(default 10). Observation and dispatch have separate selection budgets. Existing
dispatch candidates run before Work Plan reconciliation; its newly admitted
Runs can use remaining candidate slots afterward. A successful observation that
left a committed `dispatching` state can be reconsidered once in the dispatch
batch after capacity is released. Due times and quota checks still apply.
Failed/uncertain candidates and already attempted dispatches cannot run again
in follow-up. Project `max_in_flight_runs` gates new queued admissions against
started work; it does not cancel existing Runs.

`CAP-PR-ci-observation` defines current-head/current-base workflow and job evidence.
`CIProgress` re-observes immediately before merge and sends the verified head SHA
to GitHub's merge API. Its
source branches allow at most two CI-fix attempts and one conflict-fix attempt
per Run epoch before blocking; a workflow failure without an identified failed
code job pauses for environment investigation. These limits describe inspected
source; the cited examples above establish particular repair/wait outcomes, not
exhaustive test coverage of every limit.

Resume replays use durable receipts. A changed payload under an existing request
ID conflicts; a stale revision also conflicts. HTTP 404 denotes a missing resource,
409 a conflicting state/identity, 422 invalid input or an unsupported transition,
and 504 a bounded read/delivery/advance timeout where those adapters raise it.
No new error code is defined here.

The advancement source uses a 90-second budget, at most eight steps and a
120-second lease. It stops after dispatch, on unchanged workflow state or on a
future delivery due time; ordinary revision/timestamp changes do not justify
polling again. Client setup and recovery actions belong in operational guides;
the contributor's development guide owns verification commands.

## 5. Source and verification evidence

Source inspected: [`lifecycle.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/lifecycle.py),
[`ci.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/ci.py),
[`control.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/control.py),
[`delivery.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/delivery.py),
[`advancement.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/advancement.py),
[`schemas.py`](../../../modules/hub/app/features/project_management/pipeline_runs/schemas.py),
[`models.py`](../../../modules/hub/app/features/project_management/pipeline_runs/models.py),
[`catalogs.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/catalogs.py),
[`repos.py`](../../../modules/hub/app/features/project_management/pipeline_runs/repos.py),
[`pipeline/task.py`](../../../modules/hub/app/features/execution/tasks/domains/pipeline/task.py),
[`projects/api/v1.py`](../../../modules/hub/app/features/project_management/projects/api/v1.py)
and [`pipeline_runs/api/v1.py`](../../../modules/hub/app/features/project_management/pipeline_runs/api/v1.py).

The original named tests were source-inspected. Executed affected-suite and recovery checks are retained in `docs/materials/2026-11/20261105-work-item-retry/development-checks.md`. Unit tests use mock lifecycle objects and the
integration examples use controlled GitHub responses; neither source/test
inspection nor this document establishes live provider behavior, deployment of
the inspected source or Auto Hub's own SDD baseline.

## Owed items

WHILE a PR run is `paused` or `blocked` and no decision, Work Item recovery or replacement or Work
Item `attention` describes it, the run is a counted `stopped-run` owed item in `CAP-PR-owed-items`; a deliberate pause
counts too. A `failed` run is a quiet `failed-run` item without count weight that links its Work Item when one exists.
Every PR run response carries `has_pending_decision` (`CAP-PR-operator-decisions`).

## SDD activity context

WHEN an optimistic SDD activity is enrolled, Hub MUST use ordinary PR attempts,
questions, explicit resume and current-head CI without selecting repository
workflow stages or authoring its workflow decisions. Check: optimistic PR
progression tests and `pipeline_runs/requests.py` source inspection.

## Verification ownership

Repository verification MUST execute in repository-owned GitHub Actions whose
configured results Hub observes through `CAP-PR-ci-observation`. Hub MUST NOT add
a devkit evaluator, runtime installer or asset-restoration service as a delivery
prerequisite. Check: activity request, API/import and serving-image inspection.
Repository-internal setup and SDD correctness remain with the working agent.
