---
id: UC-resume-verified-pr
title: Resume a Verified Existing PR
summary: "A delivery coordinator verifies an externally implemented paused PR, obtains scoped approval for its repository evidence, and resumes its existing owner. The coordinator observes the result without creating another PR executor."
area: sdk
primary_actor: Delivery coordinator
supporting_actors:
  - Scoped approver
  - devkit-spec runtime
  - Existing PR owner
  - GitHub
status: active
capabilities:
  - CAP-SDK-existing-pr-bridge
  - CAP-SDK-task-flow-execution
---

# [UC-resume-verified-pr] Resume a Verified Existing PR

## 1. Goal

- **Goal**: deliver an externally implemented PR through its existing owner after
  checking repository evidence and obtaining approval for that evidence.
- **Scope**: the native SDK evidence-check and PR-delivery tasks.
- **Trigger**: the coordinator requests execution of the registered bridge flow.
- **Preconditions**: the coordinator knows the intended existing PR run and source
  identity; the host, runtime and checkout have been provisioned. Namespace
  authority, owner eligibility, readiness and approval are checked by the system.

## 2. Main Success Scenario

1. The coordinator requests the intended registered bridge release (`CAP-SDK-task-flow-execution`).
2. The bridge verifies repository evidence and claims the eligible paused PR run (`CAP-SDK-existing-pr-bridge`).
3. The host presents the flow as waiting for approval (`CAP-SDK-task-flow-execution`).
4. The scoped approver authorizes the checked evidence (`CAP-SDK-existing-pr-bridge`, `CAP-SDK-task-flow-execution`).
5. The bridge revalidates the approved evidence and resumes the existing PR owner (`CAP-SDK-existing-pr-bridge`).
6. The bridge observes that owner's delivery through completion (`CAP-SDK-existing-pr-bridge`).
7. The coordinator retrieves the completed delivery result (`CAP-SDK-task-flow-execution`, `CAP-SDK-existing-pr-bridge`).

## 3. Extensions

- **1a.** Release snapshot changed: the host refuses a new request with `release-mismatch`; the use case ends without a new flow run (`CAP-SDK-task-flow-execution`).
- **2a.** Invalid or unready checkout: the bridge records the capability-defined checkout/path/workflow error; the use case ends failed without resuming the PR (`CAP-SDK-existing-pr-bridge`).
- **2b.** Ineligible PR owner: the bridge records the capability-defined project, native-SDD ownership, paused-revision, head or external-implementation error; the use case ends failed without resuming the PR (`CAP-SDK-existing-pr-bridge`).
- **2c.** Another flow owns the PR: the check fails with `pr-owned-by-another-flow`; the use case ends without replacing that claim (`CAP-SDK-existing-pr-bridge`).
- **4a.** Approval command lacks scope or uses stale/conflicting identity: the host refuses with `task-scope`, `stale-revision` or `command-conflict`; this invocation ends without authorizing resume (`CAP-SDK-task-flow-execution`).
- **4b.** Approval expires: advancement records `approval-deadline`; the use case ends failed (`CAP-SDK-task-flow-execution`).
- **5a.** Approval step omitted or authority does not match evidence: delivery fails with `pr-resume-approval-required` or `pr-evidence-mismatch`; the use case ends without resume (`CAP-SDK-existing-pr-bridge`).
- **5b.** Repository evidence changes after approval: delivery records `checkout-dirty`, `checkout-head-changed` or `approved-evidence-changed`; the use case ends failed before resume (`CAP-SDK-existing-pr-bridge`).
- **5c.** PR changes before resume: the existing owner's refusal becomes `pr-resume-rejected`; the use case ends failed without a successful resume receipt (`CAP-SDK-existing-pr-bridge`).
- **5d.** Worker dies after resume: recovery finds the same durable resume receipt and continues at step 6 without another resume (`CAP-SDK-existing-pr-bridge`).
- **6a.** Owner pauses or blocks: the bridge records `pr-paused` or `pr-blocked` and keeps the flow waiting; observation resumes at step 6 after the owner progresses (`CAP-SDK-existing-pr-bridge`).
- **6b.** Owner fails or is canceled: the bridge records `pr-failed` or `pr-canceled`; the use case ends failed with the owner's state retained in the attempt output (`CAP-SDK-existing-pr-bridge`).
- **\*a.** Coordinator cancels nonterminal delivery: when a bridge worker cancellation is dispatched for an outstanding task, the bridge tombstones its claim and requests cancellation of a nonterminal owner if a delivery attempt was assigned. With no outstanding attempt, the flow cancels locally without invoking the bridge worker or tombstoning its claim; a claim without an assigned delivery attempt can be reassigned from that canceled flow. The use case ends canceled without reversing already delivered external effects (`CAP-SDK-existing-pr-bridge`, `CAP-SDK-task-flow-execution`).
- **\*b.** Temporary runtime or PR observation failure: the host retains the attempt with `worker-unavailable` for inspection/recovery; resumes at the interrupted task after the failure clears (`CAP-SDK-existing-pr-bridge`, `CAP-SDK-task-flow-execution`).

## 4. Postconditions

- **Success guarantee**: the original PR owner completed delivery; the SDK result
  identifies that existing run and its observed head, without a second PR executor.
- **Minimal guarantee**: failed evidence or approval does not authorize resume;
  after an actual resume effect, its durable identity survives worker death.
  Cancellation fences later bridge control but does not undo already posted agent
  requests, pushes or merges.

## 5. Acceptance Criteria (Given / When / Then)

Rules used: configured namespace, checkout identity/readiness, paused owner,
single claim, scoped approval, approved evidence, live PR head, resume identity,
effect recovery, owner projection and cancellation in
`CAP-SDK-existing-pr-bridge`; admission pinning, command authority/deadlines and
worker recovery in `CAP-SDK-task-flow-execution`.

### SDK-BRIDGE-01: Completes through the existing owner

- **Covers**: main success scenario.
- **Given**: a clean ready checkout and eligible paused externally implemented run.
- **When**: its checked evidence is approved and delivery progresses.
- **Then**: one resume receipt is recorded and the completed flow returns the existing PR run identity.

### SDK-BRIDGE-02: Rejects the wrong active release

- **Covers**: 1a.
- **Given**: activation selected a release different from the requested pin.
- **When**: the coordinator submits a new flow request.
- **Then**: `release-mismatch` is returned without admitting a run.

### SDK-BRIDGE-03: Rejects changed repository evidence

- **Covers**: 2a.
- **Given**: the requested checkout contains an uncommitted evidence change.
- **When**: the bridge evaluates it.
- **Then**: `checkout-dirty` is recorded and the existing PR remains unresumed.

### SDK-BRIDGE-04: Rejects an ineligible owner

- **Covers**: 2b.
- **Given**: the PR run is not paused at the supplied revision.
- **When**: the check task validates its owner.
- **Then**: `pr-must-be-paused-at-reviewed-revision` is recorded without resume.

### SDK-BRIDGE-05: Preserves exclusive ownership

- **Covers**: 2c.
- **Given**: another active flow already claims the PR run.
- **When**: a second flow checks the same owner.
- **Then**: it fails with `pr-owned-by-another-flow` and leaves the original claim intact.

### SDK-BRIDGE-06: Refuses unscoped approval

- **Covers**: 4a.
- **Given**: the owning machine has no approval scope.
- **When**: it approves the waiting bridge flow.
- **Then**: `task-scope` is returned and no bridge approval is persisted.

### SDK-BRIDGE-07: Expires unanswered approval

- **Covers**: 4b.
- **Given**: the bridge flow remains at approval past its deadline.
- **When**: maintenance advances it.
- **Then**: `approval-deadline` ends the flow without resuming the PR.

### SDK-BRIDGE-08: Rejects delivery without approval

- **Covers**: 5a.
- **Given**: a release chains the check directly to delivery without an approval.
- **When**: the delivery worker runs.
- **Then**: `pr-resume-approval-required` is recorded and no resume receipt is created.

### SDK-BRIDGE-09: Rechecks evidence after approval

- **Covers**: 5b.
- **Given**: evidence was approved and its file is then edited without committing.
- **When**: delivery first attempts resume.
- **Then**: it fails with `checkout-dirty` and leaves the PR paused.

### SDK-BRIDGE-10: Rechecks the live PR head

- **Covers**: 5c.
- **Given**: the PR head differs from the approved head before resume.
- **When**: delivery invokes the existing owner.
- **Then**: `pr-resume-rejected` is recorded without a successful resume receipt.

### SDK-BRIDGE-11: Recovers a completed resume effect

- **Covers**: 5d.
- **Given**: a worker dies after the owner persisted its resume receipt.
- **When**: the same attempt is recovered.
- **Then**: exactly one receipt remains and the worker observes the resumed owner.

### SDK-BRIDGE-12: Preserves an owner wait

- **Covers**: 6a.
- **Given**: a resumed owner becomes paused or blocked.
- **When**: the bridge observes it.
- **Then**: the flow remains waiting with `pr-paused` or `pr-blocked` and the owner state in attempt output.

### SDK-BRIDGE-13: Projects a terminal owner failure

- **Covers**: 6b.
- **Given**: a resumed owner fails or is canceled.
- **When**: the bridge observes it.
- **Then**: the flow fails with `pr-failed` or `pr-canceled` and retains that state in attempt output.

### SDK-BRIDGE-14: Fences canceled delivery

- **Covers**: *a.
- **Given**: delivery has assigned an attempt and its PR owner is nonterminal.
- **When**: the coordinator cancels the flow and the worker confirms cancellation.
- **Then**: the claim is tombstoned, both runs become canceled, and no later bridge resume is authorized.

### SDK-BRIDGE-15: Retains uncertain observation

- **Covers**: *b.
- **Given**: runtime or PR observation is temporarily unavailable.
- **When**: advancement cannot establish the attempt's outcome.
- **Then**: the same attempt remains recoverable with `worker-unavailable`, without a new execution identity.

### SDK-BRIDGE-16: Cancel locally before delivery starts

- **Covers**: *a.
- **Given**: the check task completed, the flow waits for approval and no worker attempt is outstanding.
- **When**: the coordinator cancels the flow.
- **Then**: the flow becomes canceled without invoking bridge cancellation, the PR remains paused, and its claim can be reassigned because no delivery attempt was assigned.

## 6. Verification Evidence

The [existing bridge tests](../../../modules/hub/tests/integration/features/execution/flows/test_bridge.py)
exercise real Git/CLI evidence, persisted approval, one-owner claims, head/evidence
changes, state projection and worker-death/cancellation recovery.
[Host tests](../../../modules/hub/tests/integration/features/execution/flows/test_host.py)
cover admission pinning, scoped decisions, deadlines and worker fencing.
Cancellation before delivery starts is a source-inspected boundary; the cited
bridge cancellation test covers an already assigned delivery attempt.
Those sources and tests were inspected for these scenarios; authoring the use
case did not execute them, contact a live provider or establish production merge
behavior.
