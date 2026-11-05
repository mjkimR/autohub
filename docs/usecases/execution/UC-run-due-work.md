---
id: UC-run-due-work
title: Run due scheduled work
summary: "An external scheduler triggers one bounded dispatch cycle and obtains the count of claimed executions while Hub retains each job outcome and pending recovery work."
area: execution
primary_actor: External scheduler
supporting_actors:
  - Registered task handlers
status: active
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UC-run-due-work] Run due scheduled work

## 1. Goal

- **Goal**: Advance due work and leave durable job outcomes so another tick can
  continue eligible retries and maintenance.
- **Scope**: Auto Hub's dispatcher and shared maintenance.
- **Trigger**: The external scheduler sends a dispatch request.
- **Preconditions**: Hub and its database are available, and the installation has
  registered the task handlers that its schedule configurations name.

## 2. Main Success Scenario

1. The external scheduler requests a tick using its machine identity
   (`CAP-EXEC-scheduling-maintenance`).
2. Hub verifies trigger authority and records the heartbeat
   (`CAP-EXEC-scheduling-maintenance`).
3. Hub repairs shared maintenance if needed and checkpoints the due schedule jobs
   and eligible retries (`CAP-EXEC-scheduling-maintenance`).
4. Hub executes the selected handlers within the batch budget and persists each
   job outcome (`CAP-EXEC-scheduling-maintenance`).
5. Hub completes tick housekeeping and returns the claimed execution count
   (`CAP-EXEC-scheduling-maintenance`).

## 3. Extensions

- **2a.** Missing or invalid authority: Hub refuses authentication, or returns
  HTTP 403 for an authenticated machine without dispatch scope; no dispatch cycle
  starts and the use case ends.
- **3a.** Nothing is eligible: Hub claims no jobs, still performs tick housekeeping
  and returns a zero count; the use case ends successfully.
- **4a.** A handler raises an ordinary error: Hub records that job's failure without
  enabling an automatic job retry; the cycle resumes at step 5 after the other
  selected jobs finish.
- **4b.** The batch times out or a handler is canceled: Hub records affected jobs
  as failed/retryable where their cancellation handler completes; the cycle
  resumes at step 5 after timeout handling. Process termination can interrupt this
  path and is not an exactly-once guarantee.
- **4c.** A pending maintenance item fails: Maintenance attempts the other pending
  items, reports the aggregated task failure and preserves pending work for another
  tick; the cycle resumes at step 5.

## 4. Postconditions

- **Success guarantee**: Claimed work has durable job identities and schedule
  timestamps; job outcomes and the returned dispatch count are distinct.
- **Minimal guarantee**: An authority refusal does not dispatch work. External
  provider outcomes remain subject to their owning task's recovery contract;
  schedule row locks do not certify exactly-once remote effects.

## 5. Acceptance Criteria (Given / When / Then)

The scenarios exercise authorization, due selection, checkpointing, execution
outcomes and failure isolation from `CAP-EXEC-scheduling-maintenance`.

### Scenario: Execute a due configuration

- **Covers**: main success scenario.
- **Given**: An enabled configuration is due and its handler succeeds.
- **When**: An authorized scheduler requests a tick.
- **Then**: Hub records one successful job, advances the next due time and includes
  that job in the returned count.
- **Test**: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatchers_api.py`.

### Scenario: Refuse a machine without dispatch authority

- **Covers**: 2a.
- **Given**: A machine key has no `autohub:dispatch` scope.
- **When**: It requests a tick.
- **Then**: Hub returns HTTP 403 without starting a dispatch cycle.
- **Test**: `modules/hub/tests/integration/auth/test_auth_api.py`.

### Scenario: Finish an empty cycle

- **Covers**: 3a.
- **Given**: No operator schedule or retry is due and maintenance is not yet due.
- **When**: An authorized scheduler requests a tick.
- **Then**: Hub returns `dispatched: 0` without inventing a completed job.
- **Test**: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatchers_api.py`.

### Scenario: Keep an ordinary task failure separate from trigger success

- **Covers**: 4a.
- **Given**: A due handler raises an ordinary runtime error.
- **When**: Hub dispatches it.
- **Then**: The job becomes `failure` with a request-correlated error, and the
  trigger still returns its claimed count.
- **Test**: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatchers_api.py`.

### Scenario: Bound a stalled batch

- **Covers**: 4b.
- **Given**: A selected handler exceeds the batch timeout.
- **When**: The dispatcher exhausts its budget.
- **Then**: It cancels unfinished work and records the timeout instead of waiting
  indefinitely; cancellation-aware handlers retain retryable failure outcomes.
- **Tests**: `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services_timeout.py`,
  `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services.py`.

### Scenario: Continue maintenance past a provider failure

- **Covers**: 4c.
- **Given**: Several catalogs need collection and one provider synchronization fails.
- **When**: Shared maintenance runs.
- **Then**: Other catalogs are attempted and the task reports an aggregate failure
  rather than discarding their pending work.
- **Test**: `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py`.

These acceptance references come from source/test inspection; this use case claims
no newly executed test or live scheduler check.
