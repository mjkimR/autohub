---
id: CAP-PR-ci-observation
title: Pull Request CI Observation
summary: "Auto Hub evaluates the configured GitHub Actions workflow and required jobs against the current PR head and base, without authorizing a merge. Fresh inspection and configuration-bound saved reports keep query success separate from verification success."
area: delivery
status: active
usecases:
  - UC-inspect-pull-request-ci
  - UC-deliver-pull-request
entrypoints:
  - modules/hub/app/features/project_management/pipelines/api/v1.py
  - modules/hub/app/features/project_management/pipelines/usecases/observation.py
  - modules/hub/app/features/project_management/pipelines/github.py
  - modules/hub/app/features/project_management/pipelines/gate.py
---

# [CAP-PR-ci-observation] Pull Request CI Observation

## 1. Summary

CI observation produces evidence for one configured workflow and explicitly named
jobs. `UC-inspect-pull-request-ci` serves read-only inspection; the PR executor in
`CAP-PR-pull-request-delivery` uses the same evidence but independently checks
approval and merge policy. A `passed` report alone grants no merge authority.

## 2. Scope & Boundary

- **In-Scope**: bounded same-repository GitHub Actions reads, current PR/workflow
  identity, complete job evaluation, concurrent-change detection and saved report
  applicability.
- **Out-of-Scope**: GitHub runs CI; `CAP-PROJ-project-connections` owns stored
  connector/verification configuration; `CAP-EXEC-scheduling-maintenance` owns
  task scheduling; `CAP-PR-pull-request-delivery` owns repair and merge decisions.
- **Scope Excluded**: executing repository checks on the Hub host, dispatching
  workflows from inspection, fork PR verification, non-GitHub CI and treating
  a retained report as live merge authorization.

## 3. Business Rules & Policies

1. **Read-only inspection**: WHEN immediate inspection succeeds, Hub MUST return its GitHub evidence without persisting `TaskState` or mutating GitHub. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_inspect_reads_github_without_persisting_or_exposing_token` and its GET-only GitHub fixture.
2. **Exact verification contract**: IF the required-job list is empty or contains duplicate names, THEN Hub MUST reject inspection with HTTP 422 before network access. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_empty_or_duplicate_contract_is_rejected`.
3. **Usable connector**: IF the configured connector is disabled, THEN Hub MUST reject inspection with HTTP 422 before network access. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_disabled_connector_is_rejected_before_network`.
4. **PR boundaries**: WHEN the inspected PR is closed or from another repository, Hub MUST return `closed` or `blocked` respectively without querying Actions for it. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_closed_and_fork_pulls_do_not_query_actions`.
5. **Workflow identity**: IF a workflow run does not match the configured workflow path, event, repository, PR number and current head, THEN Hub MUST exclude it from passing evidence. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_unrelated_run_never_passes`.
6. **Newest execution**: WHEN multiple matching workflow runs exist, Hub MUST evaluate the newest run rather than reuse an older successful run. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_latest_pending_run_supersedes_previous_success`.
7. **Current base evidence**: IF the matching run's PR-base SHA is missing or differs from the observed PR base, THEN Hub MUST return `waiting` instead of passing that evidence. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `test_missing_or_stale_ci_base_cannot_pass` and `test_base_change_before_observation_invalidates_old_success`.
8. **Complete job list**: WHEN deciding verification, Hub MUST read the bounded job pages before evaluating required jobs. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_jobs_are_paginated_before_decision`.
9. **Explicit success**: WHEN returning `passed`, Hub MUST require a completed successful workflow and exactly one completed successful result for each required job. Check: [`test_gate.py`](../../../modules/hub/tests/unit/features/project_management/pipelines/test_gate.py), `TestVerificationGate.test_all_required_jobs_and_workflow_must_succeed`, `test_one_success_does_not_hide_missing_required_job`, `test_duplicate_required_job_names_are_ambiguous` and `test_workflow_success_does_not_hide_unsuccessful_required_job`.
10. **Workflow failure is not masked**: IF an unlisted failing job causes the workflow to fail, THEN Hub MUST return `failed` even when required jobs succeeded. Check: [`test_gate.py`](../../../modules/hub/tests/unit/features/project_management/pipelines/test_gate.py), `TestVerificationGate.test_unlisted_failing_job_still_fails_workflow`.
11. **Concurrent change**: IF the PR identity or workflow execution changes during observation, THEN Hub MUST return `waiting` rather than certify the earlier result. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_concurrent_changes_invalidate_success`.
12. **Upstream errors remain errors**: IF upstream reads fail or return malformed data, THEN immediate inspection MUST return HTTP 502 without upstream sensitive bodies or connector tokens. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_upstream_errors_are_sanitized` and `test_malformed_upstream_data_is_not_success`.
13. **Observation versus CI outcome**: WHEN a scheduled query successfully observes failing CI, Hub MUST record a successful scheduler job with a `failed` verification result. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_schedule_dispatch_persists_report_and_distinguishes_ci_failure`.
14. **Preserved query evidence**: IF a later scheduled query fails, THEN Hub MUST preserve the previous successful-query report while recording the scheduler failure. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_schedule_dispatch_persists_report_and_distinguishes_ci_failure`.
15. **Configuration-bound reports**: IF a schedule's configuration changed since its retained report, THEN Hub MUST refuse that stale saved-report read with HTTP 404. Check: [`test_observations_api.py`](../../../modules/hub/tests/integration/features/project_management/pipelines/test_observations_api.py), `TestPipelineObservationAPI.test_schedule_dispatch_persists_report_and_distinguishes_ci_failure` and `test_schedule_changed_during_observation_does_not_save_report`.

## 4. Interfaces & Data Contracts

| Interface | Input/result |
| --- | --- |
| `POST /api/v1/pipelines/inspect` | `PipelineObservationConfig`; HTTP 200 `PipelineObservation`; GitHub reads only, no report persistence |
| `GET /api/v1/pipelines/observations/{schedule_id}` | Last successful-query report applicable to the current observation schedule; HTTP 404 when absent/inapplicable |
| `pipeline.observe` | Scheduled observation with inline `PipelineObservationConfig` |
| `pipeline.observe_project` | Scheduled observation using `project_id` and `pull_numbers`, resolved against the current saved project |

`PipelineObservationConfig` contains `repository`, `github_connector_id`, 1–10
unique positive `pull_numbers` and `verification`. `verification.workflow` is a
`.yml`/`.yaml` filename, not its display name; `required_jobs` contains 1–30 unique
exact names; `event` is `pull_request`. Unknown fields are rejected. Credentials
come from an enabled GitHub connector, not a token in this payload.

`PipelineObservation` contains `kind: pipeline_observation`, `observed_at`, the
effective configuration and per-PR `pulls`. Each pull includes number, URL,
head/base SHA, draft/mergeability, a verification result and optional workflow/job
snapshot. Results expose `status`, `reason`, `missing_jobs` and
`unsuccessful_jobs` where applicable.

| Verification status | Meaning |
| --- | --- |
| `waiting` | No current-head run, run incomplete, absent/stale base evidence or mutation during observation |
| `failed` | Overall workflow concluded `failure`; failed job names identify available code-job evidence |
| `blocked` | Fork PR or an otherwise completed workflow/required-job contract that cannot establish explicit success |
| `passed` | Current workflow/base/head and all required jobs establish explicit success |
| `closed` | PR is closed; the delivery owner separately interprets merge versus non-merge closure |

Matching uses workflow path, event, head repository, PR identity and head SHA.
The latest run is ordered by `run_number` then ID. Its recorded PR base must match
the observed PR base. Jobs use GitHub's `filter=latest`; the observer rechecks
`run_attempt`, status, conclusion and `updated_at`, then PR head/base/state.
This checks the evidence supplied by GitHub; it does not promise an atomic
snapshot across subsequent base changes or enforce repository branch rules.

The service bounds the whole observation to 60 seconds. Reads requiring list
pagination permit at most ten pages of 100 records and fail on incomplete/excess
pages. Timeout and parse errors are query errors, never synthetic verification
failures or success. Immediate configuration errors use HTTP 422; upstream and
observation-timeout errors use HTTP 502.

Scheduled writers persist only after rechecking the current schedule payload
and, for project observations, the enabled project revision. Saved-report reads
need no credential decryption or GitHub access. They return 404 before the first
report or after schedule deletion, task/type/configuration change, or an
inapplicable project configuration. Always read the report's observation time and
job history together. Scheduling itself is owned by `CAP-EXEC-scheduling-maintenance`.

## 5. Source and verification evidence

Contracts derive from [`schemas.py`](../../../modules/hub/app/features/project_management/pipelines/schemas.py),
[`github.py`](../../../modules/hub/app/features/project_management/pipelines/github.py),
[`gate.py`](../../../modules/hub/app/features/project_management/pipelines/gate.py),
[`services.py`](../../../modules/hub/app/features/project_management/pipelines/services.py)
and [`usecases/observation.py`](../../../modules/hub/app/features/project_management/pipelines/usecases/observation.py).
The named unit/API tests were read; they were not executed for this document.
Their GitHub transport is controlled, so they do not establish live CI or a new
deployment. PR dispatch/repair details belong to `CAP-PR-agent-dispatch` and
`CAP-PR-pull-request-delivery`.
