---
id: UC-deliver-pull-request
title: Deliver a Pull Request
summary: "An operator delegates an existing pull request to Auto Hub and obtains a verified merge or a visible recoverable stop. The use case covers ordinary PR delivery rather than native SDD workflow decisions."
area: delivery
primary_actor: Operator
supporting_actors:
  - GitHub
  - Agent provider
  - Repository CI
status: active
capabilities:
  - CAP-PR-pull-request-delivery
  - CAP-PR-agent-dispatch
  - CAP-PR-ci-observation
  - CAP-PR-webhook-advancement
entrypoints:
  - modules/hub/app/features/project_management/projects/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
---

# [UC-deliver-pull-request] Deliver a Pull Request

## 1. Goal

- **Goal**: obtain implementation, verification and merging of an existing PR
  under the project's automation policy without losing recovery information.
- **Scope**: ordinary Auto Hub PR delivery and operator control.
- **Trigger**: the operator asks Hub to deliver an existing PR.
- **Preconditions**: the operator can access Hub and has identified a project and
  PR; external provider/CI infrastructure exists. Hub checks project validity,
  PR eligibility, current configuration and authorization during the flow.

## 2. Main Success Scenario

1. The operator submits the PR for implementation (`CAP-PR-pull-request-delivery`).
   Interface: `UX-pipeline-runs`, `UX-enroll-pull-request`.

2. Hub records one Run with its immutable task context (`CAP-PR-pull-request-delivery`).
   Interface: `UX-pipeline-runs`.

3. Hub delivers the implementation request to the selected provider (`CAP-PR-agent-dispatch`).
   Interface: `UX-pipeline-runs`.

4. Hub observes the provider's push and the repository's verification result through scheduled or webhook advancement (`CAP-PR-agent-dispatch`, `CAP-PR-ci-observation`, `CAP-PR-webhook-advancement`).
   Interface: `UX-pipeline-runs`, `UX-attempt-history`.

5. The operator marks the PR ready when its work is acceptable (`CAP-PR-pull-request-delivery`).
   Off screen: the operator changes PR readiness in GitHub outside the Hub interface.

6. Hub rechecks merge authorization and current-head verification, then records the merged outcome (`CAP-PR-pull-request-delivery`).
   Interface: `UX-pipeline-runs`.

## 3. Extensions

- **1a.** Invalid PR or project: Hub refuses enrollment without creating a Run;
  the operator corrects the input and restarts at step 1.
   Interface: `UX-enroll-pull-request`.

- **2a.** Another active Run owns the PR: Hub returns a conflict; the operator
  inspects the existing Run and continues that delivery instead of duplicating it.
   Interface: `UX-enroll-pull-request`, `UX-pipeline-runs`.

- **3a.** Implementation already exists: Hub skips implementation delivery and
  observes CI; resumes at step 4.
   Interface: `UX-pipeline-runs`.

- **3b.** Delivery outcome is uncertain: Hub preserves the planned delivery and
  reconciles its existing marker on continuation; resumes at step 4 after delivery
  is confirmed, without a duplicate mention for that delivery.
   Interface: `UX-pipeline-runs`.

- **4a.** An identified code job fails: where automatic repair is enabled and its
  retry allowance remains, Hub requests a CI fix; resumes at step 4 after the push.
   Interface: `UX-pipeline-runs`.

- **5a.** The PR remains Draft or returns to Draft: Hub keeps merging on hold;
  resumes at step 5 when the operator authorizes readiness again.
   Interface: `UX-pipeline-runs`.

- **6a.** Automatic merge is disabled: Hub pauses after passing verification; the
  automatic-merge goal is unfinished and the operator can merge through GitHub.
   Interface: `UX-pipeline-runs`.

- **6b.** The branch conflicts with or trails its base: where automatic conflict
  repair is enabled and its allowance remains, Hub requests an update; resumes at
  step 4 after the repair push.
   Interface: `UX-pipeline-runs`.

- **6c.** A repository rule blocks merging: Hub waits without asking the agent for
  a conflict fix; resumes at step 6 when GitHub permits the merge.
   Interface: `UX-pipeline-runs`.

- **6d.** Authorization changes during observation: Hub refuses the stale
  continuation before merging; the operator inspects the current Run and the
  automatic continuation ends.
   Interface: `UX-pipeline-runs`.

- **\*a.** The operator pauses the Run: Hub stops progression and clears its
  observation lease; the flow remains unfinished until an inspected resume.
  An already sent provider request can still produce changes.
   Interface: `UX-pipeline-runs`.

- **\*b.** The operator cancels the Run: Hub ends local progression; the flow ends
  without recalling an already sent request or undoing its effects.
   Interface: `UX-pipeline-runs`.

- **\*c.** A paused Run receives a push before resume: Hub observes that push
  instead of repeating the delivered request when resuming without an answer;
  resumes at step 4.
   Interface: `UX-pipeline-runs`.

## 4. Postconditions

- **Success guarantee**: the Run records `completed` following confirmed merging;
  implementation text alone or CI for an earlier head is not a successful merge.
- **Minimal guarantee**: an enrollment refusal creates no Run; an admitted Run
  retains identities and history for recovery. A stale continuation cannot
  overwrite a newer cancellation. Stopping Hub does not undo external effects.

## 5. Acceptance Criteria (Given / When / Then)

Rules used from `CAP-PR-pull-request-delivery`: enrollment/active ownership,
catalog selection, existing implementation, approval, repairs/waits and final
authorization fences. `CAP-PR-agent-dispatch` owns mention recovery and push
signals; `CAP-PR-ci-observation` owns applicable CI evidence. The scenarios
describe observable outcomes; schemas and bounds remain in those capabilities.

### PR-01: Deliver the accepted current head

- **Covers**: main success scenario.
- **Given**: an eligible enrolled PR with completed implementation, passing required CI and automatic merge enabled.
- **When**: Hub advances the ready PR.
- **Then**: GitHub receives the verified-head merge request and the Run becomes `completed`.

### PR-02: Refuse unsafe enrollment

- **Covers**: 1a.
- **Given**: a closed or fork PR, prohibited agent mention, or disabled project.
- **When**: the operator requests enrollment.
- **Then**: enrollment is rejected and no Run is created.

### PR-03: Recover an existing owner

- **Covers**: 2a.
- **Given**: an active Run already owns the project's PR.
- **When**: enrollment is repeated.
- **Then**: Hub returns a conflict and retains the original Run.

### PR-04: Observe externally implemented work

- **Covers**: 3a.
- **Given**: the PR already contains its implementation.
- **When**: the operator enrolls it as implemented.
- **Then**: Hub records an external implementation attempt, enters CI observation and creates no implementation delivery.

### PR-05: Reconcile a lost delivery response

- **Covers**: 3b.
- **Given**: GitHub accepted the mention before Hub lost its response.
- **When**: Hub retries progression.
- **Then**: it adopts the existing comment and keeps one delivery/comment.

### PR-06: Repair failed code without approving a Draft merge

- **Covers**: 4a.
- **Given**: a Draft PR with a failed code job and automatic CI repair enabled.
- **When**: Hub advances it within the repair allowance.
- **Then**: a CI-fix attempt is delivered and no merge is requested.

### PR-07: Respect withdrawn readiness

- **Covers**: 5a.
- **Given**: passing CI and a PR returned to Draft during the final recheck.
- **When**: Hub evaluates merging.
- **Then**: the Run waits for approval and no merge is requested.

### PR-08: Respect manual merge policy

- **Covers**: 6a.
- **Given**: a ready PR with passing CI and automatic merge disabled.
- **When**: Hub advances it.
- **Then**: the Run pauses with no GitHub merge request.

### PR-09: Repair a confirmed branch conflict

- **Covers**: 6b.
- **Given**: passing CI, automatic conflict repair and GitHub reporting `dirty` or `behind`.
- **When**: Hub advances within the conflict-fix allowance.
- **Then**: a conflict-fix attempt is delivered instead of merging.

### PR-10: Wait for a repository rule

- **Covers**: 6c.
- **Given**: GitHub refuses merging because a repository rule blocks it.
- **When**: Hub classifies the refusal.
- **Then**: it waits in `awaiting_ci` without a conflict-fix attempt.

### PR-11: Fence a canceled continuation

- **Covers**: 6d, \*b.
- **Given**: cancellation commits during the final CI read.
- **When**: the previous advancement attempts to continue.
- **Then**: it is rejected, no merge request is sent and the Run remains canceled.

### PR-12: Resume a push made while paused

- **Covers**: \*c.
- **Given**: an implementation delivery followed by pause and an external push.
- **When**: the operator resumes without applying an answer.
- **Then**: Hub observes CI without another delivery.

### PR-13: Hold a paused Run without retaining its lease

- **Covers**: \*a.
- **Given**: an active Run whose operator wants to inspect the work.
- **When**: the operator pauses it.
- **Then**: the Run becomes `paused`, its lease is cleared and automatic advancement stops.

## 6. Evidence boundary

The examples derive from the source and named tests in
`CAP-PR-pull-request-delivery`, especially `test_pipeline_runs_api.py`,
`test_merge_stage.py` and `test_lifecycle.py`. Those tests were inspected rather
than executed for this document. The examples do not assert a fresh end-to-end
provider run or production deployment.
