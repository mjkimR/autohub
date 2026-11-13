---
id: ARCH-10-quality-requirements
title: Measurable quality requirements
summary: "Defines source-backed recovery, authorization, execution-bound, fairness and disclosure scenarios with measurable outcomes and exact enforcing tests. These checks do not establish an operational SLA or live-provider coverage."
status: active
---

# [ARCH-10-quality-requirements] Measurable quality requirements

## Interpretation

Each scenario states its source, stimulus, environment, required response and
measure. Its capability owns the underlying policy; `ARCH-08-crosscutting-concepts`
explains the shared mechanism. The named tests are inspected enforcement anchors,
not a claim that this document executed them. Controlled provider fixtures,
PostgreSQL contention and actual OS isolation are different evidence classes.

No scenario promises service availability, throughput or end-to-end agent/CI
latency. Time budgets are cooperative execution bounds in the named component;
lease acquisition, cleanup, external scheduling and provider completion remain
outside any broader latency promise.

## Q-01: Reconcile an accepted PR comment once

- **Source**: the dispatching process.
- **Stimulus**: it stops after GitHub accepts the mention but before persisting the response.
- **Environment**: a persisted planned delivery and controlled GitHub comment API.
- **Response**: recovery adopts the connector-authored marker under the same delivery identity.
- **Measure**: after retry, exactly one comment and one delivery row exist, with the accepted external comment ID.
- **Owner**: `CAP-PR-agent-dispatch`.
- **Check**: [test_pipeline_runs_api.py](../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py), `test_post_response_crash_is_reconciled_without_a_duplicate_mention`.

## Q-02: Reject a merge whose authority changed

- **Source**: an operator canceling an observed PR run.
- **Stimulus**: cancellation completes during the final CI read, before the merge write.
- **Environment**: a merge-eligible fixture PR and the ordinary observation controller.
- **Response**: the stale controller refuses continuation after its final read.
- **Measure**: advancement returns HTTP 409 and records zero GitHub merge requests.
- **Owner**: `CAP-PR-pull-request-delivery`, `CAP-PR-ci-observation`.
- **Check**: [test_merge_stage.py](../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py), `test_cancel_after_final_ci_read_prevents_merge`.

## Q-03: Recover an activity publication without replacement

- **Source**: a lost GitHub ref or PR publication response.
- **Stimulus**: the exact saved candidate exists but the caller did not receive success.
- **Environment**: retained claim/checkpoint and controlled GitHub API fixtures.
- **Response**: retry recovers the same branch/PR under its original request identity.
- **Measure**: no duplicate write is issued for the saved candidate; absent/closed original artifacts do not authorize replacement.
- **Owner**: `CAP-SDD-native-delivery`.
- **Check**: `modules/hub/tests/unit/features/project_management/sdd/test_activities.py`, `test_response_loss_recovers_same_saved_candidate_without_duplicate_writes`, `test_missing_original_ref_does_not_create_replacement` and `test_closed_original_pr_is_not_replaced`.

## Q-04: Recover an uncertain SDK attempt under its existing identity

- **Source**: an unavailable worker connection.
- **Stimulus**: the host cannot determine whether submission reached the worker.
- **Environment**: a persisted attempt and a worker fixture that can confirm authoritative absence.
- **Response**: the host inspects before resubmitting the same intent.
- **Measure**: recovery performs `inspect` then `submit` with one distinct attempt UUID and one attempt row; an unstructured 404 permits no new submit.
- **Owner**: `CAP-SDK-task-flow-execution`.
- **Check**: [test_host.py](../../modules/hub/tests/integration/features/execution/flows/test_host.py), `test_authoritative_absence_resubmits_same_intent`; [test_recovery.py](../../modules/hub/tests/integration/features/execution/flows/test_recovery.py), `test_unstructured_404_does_not_authorize_redispatch`.

## Q-05: Discard an SDK result after lease replacement

- **Source**: a worker delayed beyond its claimed lease.
- **Stimulus**: another advancement reclaims the expired lease before the first result arrives.
- **Environment**: a controlled clock advanced by 61 seconds and two worker continuations.
- **Response**: the first worker's completed output is discarded and recovery retains the existing attempt identity.
- **Measure**: the stale advancement returns false; exactly one attempt remains with the recovered output rather than the stale value.
- **Owner**: `CAP-SDK-task-flow-execution`.
- **Check**: [test_host.py](../../modules/hub/tests/integration/features/execution/flows/test_host.py), `test_expired_lease_reclamation_rejects_old_worker_result`.

## Q-06: Bound one PR continuation loop

- **Source**: a trigger requesting continued PR advancement.
- **Stimulus**: each observation permits another step, or an awaited step stalls.
- **Environment**: one acquired advancement lease and asynchronous lifecycle operations that honor cancellation.
- **Response**: the controller stops at its configured step limit or raises a timeout, and attempts lease release in `finally`.
- **Measure**: source defaults are at most eight loop iterations and a 90-second cooperative deadline after lease acquisition; tests reduce these to three iterations and 0.01 seconds and assert the limit/HTTP 504 plus one release call.
- **Owner**: `CAP-PR-pull-request-delivery`.
- **Check**: [advancement.py](../../modules/hub/app/features/project_management/pipeline_runs/usecases/advancement.py); [test_advancement.py](../../modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/test_advancement.py), `test_continuation_has_a_step_limit`, `test_deadline_covers_all_steps_and_releases_lease`.

## Q-07: Continue both maintenance groups across canceled ticks

- **Source**: dispatcher cancellation while maintenance work is stalled.
- **Stimulus**: repeated ticks are canceled with all selected worker slots occupied.
- **Environment**: six pending diagnostics and six pending catalogs with persisted cursor state.
- **Response**: selection reserves progress for both groups and resumes after their recorded cursors.
- **Measure**: each of three canceled invocations starts two items from each group; all six distinct items in each group start and no worker remains active after cancellation.
- **Owner**: `CAP-EXEC-scheduling-maintenance`.
- **Check**: [test_fairness.py](../../modules/hub/tests/integration/features/execution/maintenance/test_fairness.py), `test_both_groups_progress_and_rotate_after_canceled_ticks`; PostgreSQL cursor concurrency is separately checked by `test_overlapping_postgres_ticks_advance_the_shared_cursor`.

## Q-08: Preserve unrelated artifacts during diagnostic cleanup

- **Source**: a provider result and GitHub ancestry observation.
- **Stimulus**: an ordinary PR inherits a diagnostic commit without remote ownership proof.
- **Environment**: controlled test/ordinary branches and an otherwise eligible cleanup pass.
- **Response**: cleanup retains quarantine rather than treating shared ancestry as permission to mutate the ordinary PR.
- **Measure**: before explicit resolution, the ordinary PR stays open, its body/labels stay unchanged, zero branches are deleted and cleanup remains waiting for missing proof.
- **Owner**: `CAP-CONN-connection-verification`.
- **Check**: [test_ownership_recovery.py](../../modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py), `test_default_branch_inheriting_test_commit_never_grants_cleanup_ownership`.


## Q-10: Bound the scheduler's operator-facing exception detail

- **Source**: a scheduled task raising an exception.
- **Stimulus**: its exception contains a raw credential-like connection string, or an operator-safe message exceeds the formatter limit.
- **Environment**: the scheduler's operator-message selection boundary, not an arbitrary server log sink.
- **Response**: the formatter declines undeclared exception details and truncates declared safe text.
- **Measure**: arbitrary `RuntimeError`/`KeyError` examples return no operator message; the long operator-safe example is exactly 1,000 characters before request correlation is appended.
- **Owner**: `CAP-EXEC-scheduling-maintenance`.
- **Check**: [test_operator_message.py](../../modules/hub/tests/unit/features/execution/dispatchers/test_operator_message.py), `test_any_other_error_stays_in_the_logs`, `test_errors_written_for_an_operator_are_kept_on_the_job`.

## Q-11: Remove OAuth callback credentials from its access-log target

- **Source**: a Google authorization callback request.
- **Stimulus**: its URL query contains authorization `code` and `state`.
- **Environment**: the Uvicorn access-record filter for the exact callback path.
- **Response**: the filter removes that query without removing the callback path/status or unrelated request queries.
- **Measure**: the formatted callback record contains neither `code=` nor `state=`; an ordinary project's query remains unchanged and repeated filter installation creates one filter.
- **Owner**: `CAP-ACCESS-authentication-authorization`.
- **Check**: [test_access_logging.py](../../modules/hub/tests/unit/test_access_logging.py), `test_google_callback_query_is_removed_from_access_log`, `test_other_request_queries_are_preserved`, `test_filter_installation_is_idempotent`.



## Verification limits

These scenarios define checks of controlled failures and invariants. They do not
prove every possible remote race, every sensitive logging field or arbitrary
worker cooperation. Publication-lock and overlapping-cursor assertions require
PostgreSQL. Skips and fixture results cannot stand in for those environments
or for a serving-host canary. Connected-repository runtime compatibility and
internal SDD correctness are not Hub quality guarantees.
