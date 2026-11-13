---
id: UC-verify-project-connection
title: Verify a Project Agent Connection
summary: "An operator checks whether a selected agent catalog can push a verifiable change to the project's repository and pass required CI. The isolated test returns evidence and a separate cleanup state without merging the test pull request."
area: connections
primary_actor: Operator
supporting_actors:
  - GitHub
  - Selected agent provider
status: active
capabilities:
  - CAP-CONN-connection-verification
  - CAP-PR-owed-items
entrypoints:
  - modules/hub/app/features/project_management/connection_tests/api.py
  - modules/hub/app/features/project_management/connection_tests/usecases.py
---

# [UC-verify-project-connection] Verify a Project Agent Connection

## 1. Goal

- **Goal**: obtain repository-specific evidence that the selected agent can deliver a checked change before relying on that connection for development work.
- **Scope**: Auto Hub isolated connection testing.
- **Trigger**: the operator requests verification of a project's selected agent connection.
- **Preconditions**: the operator has access to Hub's project management API.

## 2. Main Success Scenario

1. The operator inspects the selected catalog's recipe and prerequisites (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

2. The operator requests a connection test (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

3. Hub records the test against the inspected project and connection configuration (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

4. Hub runs the selected provider's isolated test recipe (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

5. Hub verifies the delivered marker and required CI on the same changed PR head (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

6. Hub closes the owned test PR and removes the isolated resources when cleanup is safe (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

7. The operator reviews the verification evidence, configuration applicability and separate cleanup result (`CAP-CONN-connection-verification`).
   Interface: `UX-connection-tests`.

## 3. Extensions

- **\*a.** Unknown project or project-scoped test: Hub refuses with HTTP 404 `NOT_FOUND`; the use case ends.
  Interface: `UX-connection-tests`.

- **1a.** Connector prerequisites missing: the option is not ready and a start is refused with HTTP 422 `INVALID_REQUEST`; the use case ends without starting a test.
  Interface: `UX-connection-tests`.

- **3a.** Matching request replay: Hub returns the existing test instead of creating another; resumes at step 4 if it is running, or step 7 if it is terminal.
  Interface: `UX-connection-tests`.

- **3b.** Request identity conflict or another running test: Hub refuses with HTTP 409 `CONFLICT`; the use case ends.
  Interface: `UX-connection-tests`.

- **4a.** Catalog admission unavailable: Hub keeps the test waiting at dispatching with the admission reason and retries later; resumes at step 4 when admitted, unless cancellation/deadline ends the test.
  Interface: `UX-connection-tests`.

- **4b.** Provider creation result uncertain: Hub reconciles the original Jules attempt without issuing another create; resumes at step 4 when the session is found, or retains the uncertainty until terminal handling.
  Interface: `UX-connection-tests`.

- **4c.** Connection configuration changes: Hub requests cancellation of the old configuration's test; resumes at step 6 with a canceled outcome.
  Interface: `UX-connection-tests`.

- **4d.** Operator cancels or deadline expires: Hub records `canceled` or `timed_out`; resumes at step 6 without assuming the remote agent stopped.
  Interface: `UX-connection-tests`.

- **5a.** Marker absent/wrong, head unchanged or CI not yet passing: Hub does not declare success; resumes observation at step 5 until valid evidence or terminal handling.
  Interface: `UX-connection-tests`.

- **5b.** Definitive provider/configuration rejection or failed CI: Hub records `failed` with evidence/detail; resumes at step 6.
  Interface: `UX-connection-tests`.

- **6a.** Cleanup request fails: Hub retains the verification outcome with cleanup `failed` and retries later; resumes at step 7 with cleanup still unresolved.
  Interface: `UX-connection-tests`.

- **6b.** Failed-test delay or ambiguous Jules ownership: Hub leaves cleanup waiting and preserves protection instead of deleting unconfirmed output; resumes at step 7 with the retained terminal result and unresolved cleanup.
  Interface: `UX-connection-tests`.

## 4. Postconditions

- **Success guarantee**: the test records verified marker/current-head CI evidence for its pinned connection configuration; no test PR is merged by this workflow.
- **Minimal guarantee**: refused starts create no new test, uncertain Jules creation is not repeated, a terminal outcome survives late provider activity, and cleanup uncertainty remains visible rather than authorizing deletion of unrelated resources.
- **Owed item**: a terminal test with reviewable cleanup is a counted `connection-test-cleanup` owed item
  until its cleanup completes (`CAP-PR-owed-items`).

## 5. Acceptance Criteria (Given / When / Then)

Rules used: `CAP-CONN-connection-verification` **Recipe readiness**, **Idempotent start**,
**Conflicting start**, **Configuration identity**, **Shared admission**, **Creation reconciliation**,
**Verified head**, **No test merge**, **Terminal cancellation**, **Independent cleanup result**,
**Positive cleanup ownership**, **Delayed failed-test deletion**, **Unresolved discovery**, **Project isolation**.

### Scenario CONN-01: Verify and clean an isolated change

- **Covers**: main success scenario.
- **Given**: a configured recipe and available catalog capacity.
- **When**: the operator starts the test and the agent pushes the exact marker with passing current-head required CI.
- **Then**: the test becomes `succeeded`, retains the verified SHA/CI evidence and closes its PR without merging; safe cleanup completes separately.

### Scenario CONN-02: Refuse missing prerequisites

- **Covers**: 1a.
- **Given**: the selected Jules connector is disabled or missing.
- **When**: the operator inspects options and requests a start.
- **Then**: readiness is false and start returns HTTP 422 `INVALID_REQUEST` without creating a test.

### Scenario CONN-03: Resume the same requested test

- **Covers**: 3a.
- **Given**: an existing test for the project and selected catalog.
- **When**: the operator repeats its start request.
- **Then**: the same test ID and current record are returned without another test or provider execution.

### Scenario CONN-04: Refuse a competing start

- **Covers**: 3b.
- **Given**: a running test or a request ID already bound to a different requested catalog.
- **When**: the operator starts conflicting work.
- **Then**: HTTP 409 `CONFLICT` is returned and the original test remains the controlled record.

### Scenario CONN-05: Wait for catalog capacity or quota

- **Covers**: 4a.
- **Given**: a test ready to dispatch and a catalog with an unexpired hold or full capacity.
- **When**: the worker advances the test.
- **Then**: it stays at dispatching with the admission reason and creates no provider execution.

### Scenario CONN-06: Reconcile an uncertain Jules creation

- **Covers**: 4b.
- **Given**: Jules accepted the create request but its response was lost.
- **When**: the worker advances again.
- **Then**: the original session is reconciled and only one create request exists.

### Scenario CONN-07: Cancel an obsolete connection configuration

- **Covers**: 4c.
- **Given**: a recorded test whose connector credentials were rotated before dispatch.
- **When**: the worker advances it.
- **Then**: `configuration_current` is false, the test becomes `canceled`, and no new provider execution is created from the changed configuration. Cleanup may still reconcile existing output.

### Scenario CONN-08: Keep cancellation and timeout terminal

- **Covers**: 4d.
- **Given**: a dispatched test with cancellation requested or an elapsed deadline.
- **When**: the worker observes a later provider push.
- **Then**: the outcome remains respectively `canceled` or `timed_out`, and branch cleanup waits at least one day from finish.

### Scenario CONN-09: Require exact marker and current-head CI

- **Covers**: 5a.
- **Given**: an unchanged head, wrong marker, or skipped/missing required CI.
- **When**: the worker observes the test PR.
- **Then**: it does not declare success from those observations.

### Scenario CONN-10: Record definitive failure

- **Covers**: 5b.
- **Given**: a Jules recipe whose repository Source cannot be resolved, or a marker-verified PR with failed required CI.
- **When**: the worker advances the test.
- **Then**: the outcome is `failed` with diagnostic detail; Source preflight failure creates no GitHub resources or Jules session.

### Scenario CONN-11: Preserve success through cleanup failure

- **Covers**: 6a.
- **Given**: a successful test and a failing GitHub cleanup request.
- **When**: cleanup is attempted and later retried.
- **Then**: verification stays `succeeded`, cleanup initially reports `failed`, and a successful retry can report `completed` without merging.

### Scenario CONN-12: Preserve unresolved cleanup protection

- **Covers**: 6b.
- **Given**: a failed test still inside its one-day delay, or a terminal Jules test with an unconfirmed output candidate beyond that delay.
- **When**: cleanup advances.
- **Then**: cleanup remains waiting; the unconfirmed candidate is not closed or deleted merely because it descends from the test commit.

### Scenario CONN-13: Refuse an unknown project-scoped test

- **Covers**: *a.
- **Given**: a test belonging to another project.
- **When**: the operator requests its advancement through the wrong project's endpoint.
- **Then**: HTTP 404 `NOT_FOUND` is returned and the test is not advanced by that request.

These scenarios derive from the source and existing automated checks named in
`CAP-CONN-connection-verification`; no new live provider or cleanup execution is
asserted here. Manual cleanup reconciliation is a separate operator recovery
action whose request and refusal contracts remain in that capability.
