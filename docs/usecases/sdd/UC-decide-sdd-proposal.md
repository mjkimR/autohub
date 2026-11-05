---
id: UC-decide-sdd-proposal
title: Accept or reject a reviewed SDD proposal
summary: "A project operator publishes an acceptance or rejection against inspected proposal evidence and obtains a durable decision result. Publication remains recoverable after uncertain responses and does not bypass CI or PR merge policy."
area: sdd
primary_actor: Project operator
supporting_actors:
  - GitHub
  - devkit runtime
status: active
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-runtime-isolation
---

# [UC-decide-sdd-proposal] Accept or reject a reviewed SDD proposal

## 1. Goal

- **Goal**: Publish a reviewed proposal decision with accountable authority and a
  recoverable result, so the Planning PR can proceed under its existing CI/merge policy.
- **Scope**: Auto Hub's native proposal decision controls.
- **Trigger**: The operator chooses to accept a proposal after reviewing its evidence.
- **Preconditions**: The operator is authenticated to Auto Hub.

## 2. Main Success Scenario

1. The operator inspects the waiting proposal run and its evidence
   (`CAP-SDD-native-delivery`, rules 9–11).
2. The operator submits acceptance bound to the inspected head and run revision
   (`CAP-SDD-native-delivery`, rules 10–11).
3. Hub verifies current authority and evidence and saves publication intent
   (`CAP-SDD-native-delivery`, rules 10–13).
4. Hub authors the proposal decision in the isolated repository checkout
   (`CAP-SDD-native-delivery`, rule 11; `CAP-SDD-runtime-isolation`).
5. Hub publishes the exact candidate under the current publication fence
   (`CAP-SDD-native-delivery`, rule 13).
6. Hub records the published decision and returns the run waiting for that
   commit's CI (`CAP-SDD-native-delivery`, rules 14, 16).

## 3. Extensions

- **2a.** Operator rejects instead: The operator supplies the rejection reason;
  Hub selects rejection publication with closure answers for open worker questions;
  resumes at step 3 (`CAP-SDD-native-delivery`, rules 12, 19).
- **3a.** Rejection lacks a reason, confirmed head is absent, or decision is mixed
  with another answer: Hub refuses with HTTP 422 / `INVALID_REQUEST`; no candidate
  is published and the use case ends.
- **3b.** Head, run/project revision, binding or workflow evidence changed: Hub
  refuses with HTTP 409 / `CONFLICT`; the operator reinspects before a new decision
  and the use case ends.
- **3c.** Acceptance is held or not waiting on its own Planning branch: Hub refuses
  with HTTP 409 / `CONFLICT`; resolve the hold or inspect the correct activity and
  the use case ends. Unapplied Hub questions also prevent rejection.
- **3d.** Request ID repeats the identical completed decision: Hub returns its
  existing result without another publication; the use case reaches its goal.
- **3e.** Request ID was used for different input or actor: Hub refuses with HTTP
  409 / `CONFLICT`; the use case ends without replacing the original receipt.
- **3f.** Another preparation still owns the request: Hub returns
  `SDD_DECISION_IN_PROGRESS`; retry the same request after preparation settles and
  the use case ends in a pending state.
- **4a.** Acceptance evaluates an inactive lifecycle: Hub refuses with
  `SDD_LIFECYCLE_INACTIVE`; the use case ends without publication.
- **5a.** Stop, project change or lease loss wins the publication fence: Hub
  refuses with HTTP 409 / `CONFLICT`; the candidate is not pushed and the use case ends.
- **5b.** Push fails or its outcome is uncertain: Hub keeps the intent/candidate
  evidence; the operator retries the identical request after inspecting the failure;
  resumes at step 3 without assuming rollback or renewed approval.
- **6a.** Push succeeded but result persistence was lost: Hub reconciles the exact
  saved candidate against the remote head under the original applicable authority;
  records the existing publication without another push and reaches the goal.
- **6b.** The saved candidate was published but its authority no longer applies:
  Hub records the remote publication with `applied: false` without changing the
  run state or restoring approval; the use case ends with recorded publication
  evidence, without authorizing continuation (`CAP-SDD-native-delivery`, rule 20).

## 4. Postconditions

- **Success guarantee**: Durable decision evidence identifies the actor, decision
  candidate and publication outcome. An applicable published decision returns the
  run to CI observation for its decision commit; merge remains separately fenced.
- **Minimal guarantee**: A stale or refused decision does not grant merge authority.
  Uncertain external effects retain recovery evidence. Recovery records publication
  without restoring authority withdrawn by cancellation, project changes or questions.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDD-native-delivery` rules 10–16 and 19–20 define
current proposal authority, acceptance/rejection, durable publication, recovery
and fresh CI. `CAP-SDD-runtime-isolation` owns the evaluated runtime identity.

### SDD-DECIDE-01: Publish acceptance against reviewed evidence

- **Covers**: main success scenario.
- **Given**: A reviewing proposal waits unheld on its own Planning branch.
- **When**: The operator accepts the inspected head and current revision.
- **Then**: Hub publishes its acceptance commit once, records authority and waits
  for CI on that commit before any policy-controlled merge.

### SDD-DECIDE-02: Publish explained rejection

- **Covers**: 2a.
- **Given**: A reviewing proposal with open worker questions and no unapplied Hub question.
- **When**: The operator rejects it with a reason.
- **Then**: The rejection commit retains the reason, rejects the proposal and closes
  its worker questions; the run waits for the rejection commit's CI.

### SDD-DECIDE-03: Refuse an incomplete decision request

- **Covers**: 3a.
- **Given**: A decision omits the confirmed head, combines another answer or rejects
  without a reason.
- **When**: The operator submits it.
- **Then**: The invalid request publishes no candidate decision.

### SDD-DECIDE-04: Refuse a changed basis

- **Covers**: 3b.
- **Given**: The run revision, PR head, project binding or workflow evidence differs
  from the inspected basis.
- **When**: The operator submits the prior decision.
- **Then**: A conflict requires reinspection and the stale decision is not published.

### SDD-DECIDE-05: Keep decision holds effective

- **Covers**: 3c.
- **Given**: Acceptance has a worker hold or wrong Planning branch, or an unapplied
  Hub question stands against the run.
- **When**: The operator submits the affected decision.
- **Then**: The request conflicts and no candidate is published through that request.

### SDD-DECIDE-06: Replay a completed request

- **Covers**: 3d.
- **Given**: A request identity already records the same actor and decision input.
- **When**: The operator resubmits it after a lost response.
- **Then**: Hub returns the recorded result without another decision publication.

### SDD-DECIDE-07: Reject request identity reuse

- **Covers**: 3e.
- **Given**: The request ID belongs to different input or another actor.
- **When**: That ID is submitted for this decision.
- **Then**: A conflict preserves the original receipt.

### SDD-DECIDE-08: Wait for the current preparation owner

- **Covers**: 3f.
- **Given**: The same decision is being prepared under an unexpired owner.
- **When**: Another call reaches the preparation fence.
- **Then**: `SDD_DECISION_IN_PROGRESS` directs retry of the same request later.

### SDD-DECIDE-09: Respect inactive lifecycle at acceptance

- **Covers**: 4a.
- **Given**: The proposal head evaluates adaptive development.
- **When**: Acceptance is prepared.
- **Then**: `SDD_LIFECYCLE_INACTIVE` prevents its publication.

### SDD-DECIDE-10: Let an earlier stop prevent publication

- **Covers**: 5a.
- **Given**: A cancellation or project change wins before the bounded push fence.
- **When**: Publication rechecks authority.
- **Then**: It conflicts before the push and no stale candidate is sent.

### SDD-DECIDE-11: Retain uncertain publication evidence

- **Covers**: 5b.
- **Given**: A prepared candidate's push failed or returned an unknown result.
- **When**: The identical request is retried.
- **Then**: Hub retains its audit evidence and reconciles the original candidate
  before publishing again; the retry does not itself renew approval.

### SDD-DECIDE-12: Recover a successful push with lost storage

- **Covers**: 6a.
- **Given**: The remote head is the saved candidate, its result was not stored and
  the original authority is still applicable.
- **When**: Recovery checks the identical decision request.
- **Then**: Hub records the existing publication without another push and returns
  the applicable run to decision-commit CI observation.

### SDD-DECIDE-13: Record publication after cancellation without reviving authority

- **Covers**: 6b.
- **Given**: The remote head is the saved candidate, its result was not stored and
  the operator canceled the run before recovery.
- **When**: Recovery checks the identical decision request.
- **Then**: Hub records `publication.state: published` and
  `publication.applied: false`, leaves the run `canceled` and grants no approval
  or additional push.
- **Check**: `modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py`,
  `test_lost_database_result_recovers_exact_pushed_commit_without_publishing_again`.

## 6. Source and Verification Boundary

Publication and recovery derive from the source and regression checks linked in
`CAP-SDD-native-delivery`. These examples describe observable contracts; they do
not claim live GitHub publication, current deployment, or execution of every
integration/OS-isolation suite during documentation work.
