---
id: UC-inspect-pull-request-ci
title: Inspect Pull Request CI
summary: "An operator obtains current GitHub Actions verification evidence for explicit PRs without starting implementation or merging. The result distinguishes a successful query from passing CI and from an older saved observation."
area: delivery
primary_actor: Operator
supporting_actors:
  - GitHub Actions
status: active
capabilities:
  - CAP-PR-ci-observation
entrypoints:
  - modules/hub/app/features/project_management/pipelines/api/v1.py
---

# [UC-inspect-pull-request-ci] Inspect Pull Request CI

## 1. Goal

- **Goal**: establish what the configured CI actually proves for the intended PR
  revisions without requesting implementation or authorizing a merge.
- **Scope**: read-only CI inspection and applicable saved observation retrieval.
- **Trigger**: the operator needs verification evidence for explicit PRs.
- **Preconditions**: the operator can access Hub and has identified the intended
  repository and PRs; Hub checks connector/configuration and evidence validity.

## 2. Main Success Scenario

1. The operator selects the repository, PRs and required workflow/jobs (`CAP-PR-ci-observation`).
2. The operator requests immediate inspection (`CAP-PR-ci-observation`).
3. Hub reads the current PR and matching workflow/job evidence (`CAP-PR-ci-observation`).
4. Hub returns the applicable verification result for the operator to assess (`CAP-PR-ci-observation`).

## 3. Extensions

- **2a.** Invalid configuration or unusable connector: Hub rejects the request
  before querying GitHub; the use case ends for correction.
- **2b.** The operator requests a retained schedule report instead: Hub returns
  the applicable last successful-query report with its original observation
  time; resumes at step 4 without certifying a fresh query.
- **2c.** No applicable saved report exists: Hub returns not found; the operator
  can request a fresh inspection at step 2.
- **3a.** The PR is closed or from another repository: Hub reports the relevant
  closed/blocked boundary without querying Actions for it; resumes at step 4.
- **3b.** Current workflow or base evidence is missing, pending or changed during
  observation: Hub reports waiting; resumes at step 4 without a passing verdict.
- **3c.** The workflow fails: Hub returns a failed verification result and the
  available failed-job evidence; resumes at step 4 with a successful query.
- **3d.** Required success cannot be established: missing, ambiguous or
  unsuccessful required jobs under a successful workflow, or a completed workflow
  with a non-success conclusion other than failure, produce blocked verification;
  resumes at step 4.
- **3e.** GitHub read, parse, pagination or timeout fails: Hub reports the query
  error rather than CI failure/success; the use case ends without a fresh report.

## 4. Postconditions

- **Success guarantee**: the operator can distinguish current passing evidence,
  waits, failed/blocked/closed verification and explicitly retained older reports.
- **Minimal guarantee**: inspection creates no PR, mention, workflow dispatch,
  merge authorization or persisted report; an error is not passing evidence.

## 5. Acceptance Criteria (Given / When / Then)

Rules used from `CAP-PR-ci-observation`: read/configuration boundaries (1–4),
identity/completeness/current-base evaluation (5–11), query errors (12) and saved
observation ownership (13–15).

### CI-01: Return passing current-head and current-base evidence

- **Covers**: main success scenario.
- **Given**: a current-base/current-head matching workflow and exactly one successful result for each required job.
- **When**: the operator requests inspection.
- **Then**: Hub returns passed verification without GitHub mutations or persisted `TaskState`.

### CI-02: Reject an invalid contract before network access

- **Covers**: 2a.
- **Given**: an empty/duplicate required-job list or disabled connector.
- **When**: the operator requests inspection.
- **Then**: Hub returns invalid configuration and no GitHub request is sent.

### CI-03: Read retained evidence after a query failure

- **Covers**: 2b.
- **Given**: a successful scheduled observation followed by a failed query.
- **When**: the operator retrieves its saved report under the unchanged configuration.
- **Then**: Hub returns the original report unchanged and the job history retains the later query failure.

### CI-04: Refuse an inapplicable saved report

- **Covers**: 2c.
- **Given**: the observation schedule has no report or its payload changed after observation.
- **When**: the operator requests the saved report.
- **Then**: Hub returns not found rather than evidence for the old configuration.

### CI-05: Stop at the PR boundary

- **Covers**: 3a.
- **Given**: a closed PR or a fork head repository.
- **When**: Hub inspects the PR.
- **Then**: it reports closed or blocked respectively without querying Actions.

### CI-06: Wait for applicable evidence

- **Covers**: 3b.
- **Given**: a newer pending workflow, mismatched/missing recorded base, or PR/run mutation during observation.
- **When**: Hub evaluates the available evidence.
- **Then**: it returns waiting even if an older workflow succeeded.

### CI-07: Keep workflow failure distinct from query failure

- **Covers**: 3c.
- **Given**: the overall workflow failed because an unlisted job failed.
- **When**: Hub successfully reads the workflow and jobs.
- **Then**: verification is failed, and scheduled observation can still record a successful scheduler job.

### CI-08: Refuse ambiguous or incomplete required success

- **Covers**: 3d.
- **Given**: the workflow reports success but a required job is missing, duplicated, skipped or otherwise unsuccessful.
- **When**: Hub evaluates the completed workflow.
- **Then**: it reports blocked instead of passing the PR.

### CI-09: Preserve upstream error boundaries

- **Covers**: 3e.
- **Given**: GitHub returns a failed read or malformed response.
- **When**: immediate inspection executes.
- **Then**: Hub returns a query error without the upstream sensitive body, connector token or invented verification result.

The scenarios derive from the inspected gate/API tests named in
`CAP-PR-ci-observation`. They were not executed while authoring and establish no
live GitHub run or current deployment claim.
