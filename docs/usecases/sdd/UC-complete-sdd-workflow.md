---
id: UC-complete-sdd-workflow
title: Complete a bound native SDD workflow
summary: "A project operator previews initial workflow waits, inspects safe diagnostics and advances a bound spec PR through worker evidence and integration authority. Holds and revisioned decisions remain effective across retries."
area: sdd
primary_actor: Project operator
supporting_actors:
  - Agent provider
  - devkit runtime
  - GitHub
  - Repository CI
status: active
capabilities:
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
---

# [UC-complete-sdd-workflow] Complete a bound native SDD workflow

## 1. Goal

- **Goal**: Complete the bound spec's workflow and deliver its existing PR with
  inspected evidence and applicable integration authority.
- **Scope**: Auto Hub native workflow control after the spec and PR exist.
- **Trigger**: The operator requests native execution of that spec PR.
- **Preconditions**: The operator is authenticated; the spec and PR exist.
  Their binding, runtime, workflow evidence and authority are checked by Hub.

## 2. Main Success Scenario

1. The operator inspects the selected spec PR's initial workflow context before registering native execution
   (`CAP-SDD-workflow-control`, rules 1, 22–23).
   Interface: `UX-sdd-execution`.

2. Hub checks the binding and the runtime the PR head's lock pins, and retains the
   evaluated execution identity
   (`CAP-SDD-workflow-control`, rule 1; `CAP-SDD-runtime-isolation`, rules 1–21).
   Interface: `UX-sdd-execution`.

3. Hub dispatches stage work and evaluates its reported outcome until integration
   approval is required (`CAP-SDD-workflow-control`, rules 12, 17–18).
   Interface: `UX-sdd-run`, `UX-sdd-execution`.

4. The operator reviews the inspected evidence and approves integration
   (`CAP-SDD-workflow-control`, rules 3, 6).
   Interface: `UX-decision-inbox`, `UX-sdd-run`.

5. Hub continues the authorized workflow through integration and its final checks
   (`CAP-SDD-workflow-control`, rules 4–6, 19; `CAP-SDD-runtime-isolation`, rule 24).
   Interface: `UX-sdd-run`.

6. The operator marks the PR ready for merge (`CAP-SDD-workflow-control`).
   Off screen: the operator changes the PR draft status in GitHub outside Hub.

7. Hub delegates current-head CI and merge authorization to the existing PR owner
   and records that owner's outcome (`CAP-SDD-workflow-control`, rule 21).
   Interface: `UX-pipeline-runs`.

The operator can locate the pending subject through `UX-decision-inbox` before opening its exact owner review. Optional notice-link entry follows `UC-receive-decision-notice`; authentication and exact current identity are checked before the existing owner controls enable. Native review refreshes and persists the current inspection basis before controls enable. Existing per-run entry points remain available.

## 3. Extensions

- **2a.** Binding/runtime admission fails: Hub reports failed readiness or refuses
  enrollment with the capability-defined invalid request/runtime error and safe diagnostic guidance,
  including `SDD_RUNTIME_UNLOCKED` for a head without a devkit lock; the use
  case ends without successful native enrollment.
   Interface: `UX-sdd-execution`.

- **2b.** Registration is eligible but the inspected workflow already waits for input: the operator can register with that wait disclosed; resumes at step 3 with the existing hold or decision channel unchanged.
   Interface: `UX-sdd-execution`.

- **2c.** The head's runtime is still being installed: readiness is false with the
  `SDD_RUNTIME_PREPARING` diagnostic (retry `safe`) and enrollment is refused with
  HTTP 503; the operator checks readiness again after the install and the use case
  resumes at step 1.
   Interface: `UX-sdd-execution`.

- **3a.** A worker problem or malformed envelope holds the unit: Hub blocks and
  reports the required recovery; after the problem is fixed and devkit reports
  its resolution, reinspection resumes at step 3 without treating resume as approval.
   Interface: `UX-sdd-run`.

- **3b.** A worker question is open: the operator chooses an offered option or
  supplies a decision outside them; Hub records an answer-envelope instruction
  and the agent publishes it before evaluation resumes at step 3. Invalid answers
  are refused with HTTP 422 and the question remains pending.
   Interface: `UX-decision-inbox`, `UX-sdd-workflow-request`.

- **3c.** Another workflow request is open: the operator answers its current options;
  Hub retains the CLI-authored publication artifact and dispatches publication;
  resumes at step 3 only after repository evidence permits it. Unsupported handoff
  anchors are refused instead of arbitrarily rebinding the run.
   Interface: `UX-decision-inbox`, `UX-sdd-workflow-request`.

- **3d.** The operator applies a stored run clarification: Hub dispatches that selected
  direction and carries it into later stages; resumes at step 3. A no-change answer
  can return to the gate without a fabricated push; answering is not approval.
   Interface: `UX-decision-inbox`, `UX-run-decisions`.

- **3e.** A later head's lock pins another runtime: if it is cached, Hub
  evaluates with it, records the new runtime identity and continues at step 3; if
  it is still being installed, Hub keeps the run's state, records the
  `SDD_RUNTIME_PREPARING` diagnostic and inspects the head again on a later
  dispatcher tick, returning to step 3 once the install completes; after 45
  minutes of preparing, Hub blocks the run with a remediation reason and the
  operator resumes it after fixing the runtime setup.
   Interface: `UX-sdd-run`.

- **4a.** Ready status or pinned auto policy already authorizes the unheld gate:
  Hub records the observed/policy authority; resumes at step 5 without inventing
  a human actor or bypassing withheld approval.
   Interface: `UX-sdd-run`.

- **4b.** The operator requests rework: Hub requires nonblank feedback and a changed
  head, withdraws approval and dispatches the work; resumes at step 3. An unchanged
  attempt times out after 45 minutes and remains blocked until inspected continuation.
   Interface: `UX-sdd-run`.

- **4c.** The operator revokes integration authority: Hub blocks and preserves
  withheld approval through ready observations and generic resume; resumes at step
  4 only after explicit reapproval against applicable evidence.
   Interface: `UX-sdd-run`.

- **4d.** The operator rejects integration: Hub records cancellation; the use case
  ends without recalling external work already sent.
   Interface: `UX-sdd-run`.

- **4e.** New decision uses stale evidence/revision, changed request identity or
  mixed direction inputs: Hub refuses with the capability-defined conflict or
  invalid-request response; the invocation ends without that requested transition.
   Interface: `UX-sdd-run`.

- **5a.** The base moves and workflow integration is no longer complete: Hub
  reintegrates under the applicable recorded intent before resuming at step 7.
   Interface: `UX-sdd-run`.

- **5b.** Observed readiness is withdrawn or an unexpected head change invalidates
  authority: Hub clears approval and blocks; reinspection returns to step 4.
   Interface: `UX-sdd-run`.

- **5c.** Workflow/configuration drift or final recorded-rule loading prevents
  evaluation: Hub blocks with the runtime contract's structured remediation rather than
  dispatching repair for that setup failure; the invocation ends pending recovery.
   Interface: `UX-sdd-run`.

- **6a.** The PR stays draft: integration may finish under its recorded authority,
  but merging waits; resumes at step 6 when the operator marks it ready.
   Interface: `UX-sdd-run`.

- **7a.** Required CI or project merge policy prevents merge: the existing PR owner
  retains its wait, permitted repair or policy-controlled stop; the automatic
  completion path remains unfinished until that condition is resolved.
   Interface: `UX-pipeline-runs`.

- **\*a.** The operator manually pauses the run: Hub removes automatic approval-wait
  polling eligibility; the workflow remains unfinished until inspected continuation.
   Interface: `UX-pipeline-runs`.

- **\*b.** A matching decision receipt is replayed: Hub returns current run state
  without repeating the earlier transition or undoing a later stop; the invocation
  ends with the recorded outcome.
   Interface: `UX-run-decisions`, `UX-sdd-run`, `UX-sdd-workflow-request`, `UX-sdd-decision-history`.

- **4z.** The inbox subject resolved, changed generation or failed inspection: controls remain disabled and the operator refreshes the list and explicitly reviews the current subject; resumes at step 4.
   Interface: `UX-decision-inbox`, `UX-run-decisions`.

The retained owner review keeps the exact selected decision outcome after its pending request disappears. Check outcome reads the selected durable owner request; Retry same request retains its original input through refresh and temporary close. A reload explains that unacknowledged in-memory intent is unavailable. Recorded authority, matched worker publication, proposal candidates and current Run state remain separate facts in `UX-run-decisions`, `UX-sdd-workflow-request` and `UX-sdd-run`.

## 4. Postconditions

- **Success guarantee**: The existing PR owner records completion after the native
  workflow and applicable CI/merge conditions succeed. No second PR executor is created.
- **Minimal guarantee**: A held unit, stale decision or generic resume does not
  grant integration authority. Recorded decision/request identities survive retries;
  pause/cancel does not undo an already delivered external effect.

## 5. Acceptance Criteria (Given / When / Then)

Rules used: `CAP-SDD-workflow-control` rules 1–21 own binding, stage work, decisions,
publication, held evidence and PR-owner delegation. `CAP-SDD-runtime-isolation`
owns the evaluated runtime and configuration identity.

### SDD-COMPLETE-01: Deliver through one native PR owner

- **Covers**: main success scenario.
- **Given**: An eligible spec PR reaches an unheld integration gate with inspected evidence.
- **When**: The operator approves, the workflow integrates, the PR is ready and its required CI passes.
- **Then**: The same PR owner completes the merge and retains the approval receipt.

### SDD-COMPLETE-02: Refuse an invalid admission

- **Covers**: 2a.
- **Given**: The selected unit's PR is on another activity branch or its head has no root `uv.lock` declaring `devkit-spec`.
- **When**: The operator checks/enrolls native execution.
- **Then**: Readiness is false or enrollment is refused without a successful native run.

### SDD-COMPLETE-24: Report a runtime still being prepared

- **Covers**: 2c.
- **Given**: No cached runtime exists for the PR head's lock identity.
- **When**: The operator checks readiness.
- **Then**: Readiness is false with an `SDD_RUNTIME_PREPARING` runtime diagnostic whose retry is `safe`, one install starts, and a later check after it completes can be eligible.

### SDD-COMPLETE-25: Continue with a changed runtime identity

- **Covers**: 3e.
- **Given**: An admitted run's snapshot names one runtime identity and its next head locks another with the same effective workflow, policy and configuration.
- **When**: Hub evaluates the next head.
- **Then**: The run continues and its snapshot records the new `devkit-lock:<identity>`; a changed effective workflow is still refused.

### SDD-COMPLETE-26: Wait for a runtime that is still installing

- **Covers**: 3e.
- **Given**: A running native run whose next head's runtime is still being installed.
- **When**: The dispatcher observes the run.
- **Then**: The run keeps its state without a pause reason and its progress carries the `SDD_RUNTIME_PREPARING` diagnostic.

### SDD-COMPLETE-03: Require resolved worker evidence

- **Covers**: 3a.
- **Given**: Devkit reports an unresolved worker problem.
- **When**: The operator resumes or tries approval before its resolution.
- **Then**: The hold remains effective and no integration/merge authority is granted.

### SDD-COMPLETE-04: Publish a worker answer through its own channel

- **Covers**: 3b.
- **Given**: A worker question offers two choices.
- **When**: The operator selects one with a decision note.
- **Then**: Hub retains an answer-envelope instruction with user authority, not a generic YAML decision record; evaluation waits for publication.

### SDD-COMPLETE-05: Refuse an invalid worker answer

- **Covers**: 3b.
- **Given**: A worker question remains open.
- **When**: The operator declines it, chooses a nonexistent option or supplies an empty outside-options decision.
- **Then**: HTTP 422 leaves the question pending without the requested answer transition.

### SDD-COMPLETE-06: Publish an authorized handoff answer

- **Covers**: 3c.
- **Given**: An open handoff offers an eligible workflow for the same spec anchor.
- **When**: The operator accepts it against current evidence.
- **Then**: Hub records the selected ID/hash and publication artifact; unrelated workflow/runtime/policy changes remain unauthorized.

### SDD-COMPLETE-07: Keep handoff anchors bounded

- **Covers**: 3c.
- **Given**: A selected handoff requires another anchor type.
- **When**: The operator submits its acceptance.
- **Then**: Hub refuses that transition and requires separately enrolled work instead.

### SDD-COMPLETE-08: Preserve selected no-change clarification

- **Covers**: 3d.
- **Given**: A stored clarification has one selected answer and an unselected alternative.
- **When**: The selected answer is applied and the agent determines no code change is needed.
- **Then**: Later stage instructions retain only selected direction; the run can return to the integration gate without a fabricated push or automatic approval from the answer itself.

### SDD-COMPLETE-09: Record observed PR-ready authority

- **Covers**: 4a.
- **Given**: An unheld integration gate has no withheld authority and its PR is ready.
- **When**: Hub observes the gate.
- **Then**: Authorization records `github:pr-ready` with inspected head/base/evidence; a guessed human actor is not used.

### SDD-COMPLETE-10: Preserve a timed-out rework requirement

- **Covers**: 4b.
- **Given**: Explicit rework remains on its prior head after 45 minutes.
- **When**: The operator generically resumes the blocked run.
- **Then**: Rework remains required and the retry does not restore approval.

### SDD-COMPLETE-11: Keep revocation effective

- **Covers**: 4c.
- **Given**: Integration approval was revoked while the PR remains ready.
- **When**: Generic resume or another ready observation occurs.
- **Then**: Approval remains withheld until explicit applicable reapproval.

### SDD-COMPLETE-12: Reject integration without recalling provider work

- **Covers**: 4d.
- **Given**: A native workflow is waiting for integration direction.
- **When**: The operator rejects integration.
- **Then**: Hub records a canceled run and no Hub merge; previously sent remote work is not claimed canceled.

### SDD-COMPLETE-13: Refuse stale direction

- **Covers**: 4e.
- **Given**: The run/evidence changed after inspection, or a request ID belongs to another payload.
- **When**: New direction is submitted with the old basis or reused identity.
- **Then**: The request conflicts without applying that transition.

### SDD-COMPLETE-14: Reintegrate a moved base

- **Covers**: 5a.
- **Given**: An approved workflow's base changes and devkit requires integration again.
- **When**: Hub observes it before merging.
- **Then**: Workflow integration resumes instead of merging from the old completed result.

### SDD-COMPLETE-15: Respect changed readiness/head

- **Covers**: 5b.
- **Given**: Approval observed a ready PR and it returns to draft or moves to an unexpected head.
- **When**: Hub reinspects it.
- **Then**: Authorization is cleared and the run blocks before merge.

### SDD-COMPLETE-16: Block unrepairable runtime drift

- **Covers**: 5c.
- **Given**: A recorded stale-receipt rule cannot load during final lint.
- **When**: Hub advances or generically resumes.
- **Then**: It retains the receipt remediation diagnostic without another repair attempt.

### SDD-COMPLETE-17: Keep draft separate from integration authority

- **Covers**: 6a.
- **Given**: Explicit integration authority exists on a draft PR.
- **When**: The workflow integrates successfully.
- **Then**: Hub waits for PR readiness before merging.

### SDD-COMPLETE-18: Retain final verification/policy waits

- **Covers**: 7a.
- **Given**: Native integration completed but required CI is pending or automatic merge is disabled.
- **When**: The PR owner advances.
- **Then**: It waits or takes its configured policy stop without a merge.

### SDD-COMPLETE-19: Keep manual pause separate from gate polling

- **Covers**: *a.
- **Given**: A run is automatically polling an integration approval wait.
- **When**: The operator pauses it manually and the PR later becomes ready.
- **Then**: Automatic approval-wait eligibility is cleared and the run remains paused.

### SDD-COMPLETE-20: Replay without repeating direction

- **Covers**: *b.
- **Given**: A successful decision receipt exists and the run was subsequently stopped.
- **When**: The identical request is replayed.
- **Then**: Hub returns current state without repeating approval/publication or undoing the stop.

### SDD-COMPLETE-21: Preview a registered workflow wait

- **Covers**: 2b and step 1.
- **Given**: An eligible spec PR has a reported stage, pending question or approval request.
- **When**: The operator checks readiness.
- **Then**: The preview distinguishes registration eligibility from that existing wait and shows effective approval policy without answering or approving it.

### SDD-COMPLETE-22: Retain safe diagnostic guidance

- **Covers**: 2a and 5c.
- **Given**: Runtime evaluation returns a recognized notice or fails with a recognized error.
- **When**: The operator inspects readiness or the retained native run.
- **Then**: Hub-authored code, responsibility and recovery guidance appear without copying arbitrary upstream message, path, command or stderr into the diagnostic record.

### SDD-COMPLETE-23: Reinspect a changed registration selection

- **Covers**: step 1.
- **Given**: Readiness was inspected for one unit and PR.
- **When**: The operator changes that selection or an older request completes.
- **Then**: The previous preview cannot enable registration for the changed combination; a matching inspection is required.

## 6. Source and Verification Boundary

The scenarios map to the native, human-direction, workflow-decision and runtime
checks linked in the owning capabilities. These are contracts derived from source
and inspected regression tests, not a claim that every variant above was executed
or that a live provider published envelopes and completed a merge. The full choice
validation/path matrix and some runtime-failure combinations remain source-inspected.

### INBOX-01: Preserve exact owner review

- **Given** an observed pending decision in the shared inbox,
- **When** the operator selects Review,
- **Then** the exact owner subject loads and native controls wait for persisted inspection; an obsolete selection stays disabled until explicit reinspection.
- **Covers**: 4z and the discovery entry.


### CONTINUE-01: Follow recorded native direction without inferring completion

- **Covers**: *b, 3b, 4e.
- **Given** recorded native direction with uncertain publication or a later stop,
- **When** the operator checks its exact outcome or explicitly reviews publication reconciliation,
- **Then** missing proof remains unknown/pending, historical direction does not restore current authority, and separately identified recovery preserves the original intent and later stop guards.

## 7. Batch ancestry

When entered from `UC-execute-sdd-batch`, the operator follows the exact owner through `UX-sdd-batch` into the existing run controls. The batch retains original proposal/current SPEC ancestry and observes this owner's result. Its receipt is no plan-accept, handoff or integration approval. Success of this use case supplies owner evidence; only the batch's fresh exact prerequisite/lineage checks can release its next member. The batch creates no second PR executor (`CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`).
