---
id: UC-execute-task-flow
title: Execute a Versioned Task Flow
summary: "A machine client registers and runs a versioned task flow, resolves any declared approval, and obtains its durable result. The host preserves identities and execution limits across retries and recovery."
area: sdk
primary_actor: Machine client
supporting_actors:
  - Configured worker
  - Scoped approver
  - Maintenance scheduler
status: active
capabilities:
  - CAP-SDK-task-flow-execution
---

# [UC-execute-task-flow] Execute a Versioned Task Flow

## 1. Goal

- **Goal**: obtain the result of a declared task flow without creating duplicate
  work after a retry or lost response.
- **Scope**: SDK release/run API and the durable host executor.
- **Trigger**: a machine client requests execution of a task or sequential flow.
- **Preconditions**: the host and its maintenance scheduler are available; the
  client has the task definitions and intended inputs. Authentication, ownership,
  target configuration and schema validity are checked by the system.

## 2. Main Success Scenario

1. The client registers the flow definition and configured task bindings (`CAP-SDK-task-flow-execution`).
2. The client activates the registered release at the observed environment revision (`CAP-SDK-task-flow-execution`).
3. The host admits the execution request against an immutable release snapshot (`CAP-SDK-task-flow-execution`).
4. The host advances the ordered tasks through configured workers until a declared approval is reached (`CAP-SDK-task-flow-execution`).
5. The scoped approver authorizes continuation of the waiting flow (`CAP-SDK-task-flow-execution`).
6. The host completes the remaining tasks and validates the flow result (`CAP-SDK-task-flow-execution`).
7. The client retrieves the completed run and its result (`CAP-SDK-task-flow-execution`).

## 3. Extensions

- **1a.** Invalid definition or target: the host refuses malformed wire data with `request-invalid`, invalid schema/reference/host limits with their capability-defined codes, or an unavailable binding with `worker-binding`; the use case ends without a registered release.
- **1b.** Conflicting release identity: the host refuses changed content under an existing release identity with `release-conflict`; the use case ends.
- **2a.** Activation cannot proceed: an absent release produces `release-not-found`, or a stale revision produces `stale-revision`; the use case ends without changing the active release.
- **3a.** Admission cannot proceed: an absent environment, inactive release, unknown contract, invalid input or changed expected release produces the corresponding capability-defined refusal; the use case ends without a new run.
- **3b.** Request replay: the same request returns the existing run and resumes at its observed progress; changed content under its identity produces `request-conflict` and the use case ends.
- **4a.** Uncertain worker outcome: the host retains the attempt for inspection with `worker-unavailable`; authoritative absence permits resubmission under the same identity; resumes at step 4.
- **4b.** Task failure or exhausted budget: the host exposes the task's error or `attempt-limit`; a permitted explicit resume returns to step 4, otherwise the use case ends failed.
- **4c.** No approval declared: after step 4 the host proceeds directly to step 6.
- **5a.** Stale, conflicting or disallowed command: the host refuses with `stale-revision`, `command-conflict`, `revision-limit`, `approval-expired` or `invalid-command`; the client must inspect current state before another decision; this invocation ends.
- **5b.** Revision requested: the scoped approver requests permitted rework; the host preserves consumed attempt counts and resumes at step 4.
- **5c.** Approval deadline elapses: maintenance records `approval-deadline`; the use case ends failed.
- **6a.** Output violates the contract: the host records `worker-output-invalid` or `flow-output-invalid`; the use case ends failed without a successful result.
- **\*a.** Missing authority: the host refuses missing credentials with `unauthorized`, missing task scope with `task-scope`, or another machine's environment with `environment-owner`; the invocation ends without the requested mutation.
- **\*b.** Cancellation requested while the run is nonterminal: the host cancels directly when no worker attempt is outstanding, otherwise retains cancellation until a terminal worker result confirms it; the use case ends canceled.

## 4. Postconditions

- **Success guarantee**: the durable run is completed with schema-valid output and
  the release snapshot selected at admission.
- **Minimal guarantee**: a refused request does not perform its requested mutation;
  worker effects already delivered may remain after failure/cancellation, with
  durable attempt identity and fencing retained for reconciliation.

## 5. Acceptance Criteria (Given / When / Then)

Rules used: declared graph/bindings; machine boundary; release/activation/run
identity; admission snapshot and expected release; command identity/revision;
approval authority/deadline; cumulative attempts; durable dispatch/recovery;
late-result fencing; output validation and confirmed cancellation, all owned by
`CAP-SDK-task-flow-execution`.

### SDK-EXEC-01: Completes the declared flow

- **Covers**: main success scenario.
- **Given**: configured workers and a valid flow containing an approval.
- **When**: the client activates and submits it and the approver authorizes the waiting flow.
- **Then**: execution completes with validated output and the original release snapshot.

### SDK-EXEC-02: Rejects an invalid release

- **Covers**: 1a.
- **Given**: a release with an undeclared worker target.
- **When**: the client registers it.
- **Then**: the host returns `worker-binding` and stores no release for that request.

### SDK-EXEC-03: Protects release identity

- **Covers**: 1b.
- **Given**: a registered release.
- **When**: the client registers different content under its existing identity.
- **Then**: the host returns `release-conflict` and preserves the original release.

### SDK-EXEC-04: Refuses stale activation

- **Covers**: 2a.
- **Given**: an environment whose revision has advanced.
- **When**: activation uses the earlier revision.
- **Then**: the host returns `stale-revision` and leaves the active release unchanged.

### SDK-EXEC-05: Refuses admission against a changed release

- **Covers**: 3a.
- **Given**: an active release different from the client's expected snapshot.
- **When**: the client submits a new pinned request.
- **Then**: the host returns `release-mismatch` without creating a run.

### SDK-EXEC-06: Reconciles a repeated request

- **Covers**: 3b.
- **Given**: a previously admitted request.
- **When**: the same key and content are submitted again.
- **Then**: the host returns that run; changed content returns `request-conflict`.

### SDK-EXEC-07: Recovers unknown delivery

- **Covers**: 4a.
- **Given**: a persisted intent whose submit response was lost.
- **When**: the host recovers it.
- **Then**: it inspects the same attempt and resubmits only after authoritative absence; an unstructured 404 leaves the result uncertain.

### SDK-EXEC-08: Keeps the task attempt budget

- **Covers**: 4b.
- **Given**: a failed task at its declared attempt limit.
- **When**: explicit resume is requested.
- **Then**: the host returns `attempt-limit` and creates no extra attempt.

### SDK-EXEC-09: Refuses an outdated decision

- **Covers**: 5a.
- **Given**: a waiting flow whose revision has advanced.
- **When**: a new command carries the earlier revision.
- **Then**: the host returns `stale-revision` without applying the decision.

### SDK-EXEC-10: Reworks within declared bounds

- **Covers**: 5b.
- **Given**: a waiting approval with an available revision and task attempt budget.
- **When**: an authorized revision is requested.
- **Then**: execution returns to the declared earlier task while prior attempts remain counted.

### SDK-EXEC-11: Records approval expiry

- **Covers**: 5c.
- **Given**: a waiting flow past its approval deadline.
- **When**: maintenance advances it.
- **Then**: the run fails with `approval-deadline`; a late approval command is refused with `approval-expired` before advancement.

### SDK-EXEC-12: Blocks invalid output

- **Covers**: 6a.
- **Given**: a task returns output outside its declared schema.
- **When**: the host applies the result.
- **Then**: the run fails with `worker-output-invalid` and no downstream task starts.

### SDK-EXEC-13: Runs without an approval step

- **Covers**: 4c.
- **Given**: a valid single-task release without approval.
- **When**: maintenance advances its successful worker result through completion.
- **Then**: the client receives completed output without issuing an approval command.

### SDK-EXEC-14: Enforces approval scope

- **Covers**: *a.
- **Given**: the owning machine has write/read scope without approval scope.
- **When**: it attempts approval.
- **Then**: the host returns `task-scope` and keeps the approval waiting.

### SDK-EXEC-15: Cancels an outstanding worker

- **Covers**: *b.
- **Given**: a worker may have accepted an attempt.
- **When**: the client cancels the run.
- **Then**: the host retains `canceling` through uncertain responses and records `canceled` after a terminal result; a stale completed result cannot bypass the fence.

## 6. Verification Evidence

The acceptance examples map to existing tests in
[host contracts](../../../modules/hub/tests/integration/features/execution/flows/test_host.py),
[recovery](../../../modules/hub/tests/integration/features/execution/flows/test_recovery.py),
[managed-key authorization](../../../modules/hub/tests/integration/features/execution/flows/test_auth.py)
and [SDK model/transport tests](../../../packages/sdk/tests/test_remote_contract.py).
They were inspected during authoring; this document does not claim they were
executed or that production workers/providers were contacted.
