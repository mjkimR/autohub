---
id: ARCH-08-crosscutting-concepts
title: Crosscutting execution and trust concepts
summary: "Explains the shared identity, concurrency, authorization and disclosure patterns used across Auto Hub's execution paths, including their deliberate per-path exceptions. Exact product policies remain with the owning capabilities."
status: active
---

# [ARCH-08-crosscutting-concepts] Crosscutting execution and trust concepts

## Purpose and scope

PR delivery, native SDD, SDK flows, connection diagnostics and scheduling share
infrastructure without sharing one state machine or approval subject.
`ARCH-05-1-containers` locates their building blocks; `ARCH-06-execution` describes
how they advance. This section explains the concepts that recur across them.
Capabilities own protocol fields, thresholds, refusals and state transitions.
`ARCH-10-quality-requirements` identifies measurable checks of these concepts.

## Durable identity before uncertain effects

Product controllers retain an operation identity before asking another system
to perform work. A timeout or process death can leave a successful external
operation without a recorded response. Recovery uses the retained identity and
authoritative observations rather than treating a missing response as failure.

PR dispatch reconciles a connector-authored marker for the planned delivery
(`CAP-PR-agent-dispatch`). Activity publication records its exact branch/PR candidate and
later reconciles that retained identity (`CAP-SDD-native-delivery`). SDK
workers inspect the existing attempt before any authorized resubmission
(`CAP-SDK-task-flow-execution`); retired bridge delivery only observes an exact existing owner's
resume receipt (`CAP-SDK-existing-pr-bridge`). Connection diagnostics distinguish
provider ownership proof from a guessed or merely related PR
(`CAP-CONN-connection-verification`).

These mechanisms do not make arbitrary remote work exactly once. An SDK worker
must cooperate with attempt receipts and cancellation handling. An agent request
already posted can continue after Hub pauses or cancels. A scheduler's claimed
job records one scheduler execution; registered task handlers retain responsibility
for the external semantics of the work they perform.

Implementation anchors are
[PR delivery](../../modules/hub/app/features/project_management/pipeline_runs/usecases/delivery.py),
[activity publication](../../modules/hub/app/features/project_management/sdd/activities.py),
[SDK worker](../../modules/hub/app/features/execution/flows/worker.py) and
[connection ownership](../../modules/hub/app/features/project_management/connection_tests).

## Concurrency fences and transaction boundaries

A database claim limits competing local continuations. Revision checks identify
changes to the approved or observed state; leases additionally limit the time
and identity of a worker's authority. Persisting a result is conditional on the
path still owning those fences. A database lock does not make a remote API call
transactional with the local commit.

Ordinary PR observation prepares its checkpoint in a short transaction, releases
locks during external I/O, then rechecks run/project revision, lease and active
attempt/delivery identity. Cancellation can therefore finish while an observer
waits, and the stale observer cannot retain an authorized merge decision.
`CAP-PR-pull-request-delivery` owns that continuation contract.

Activity claims preserve exact request and candidate identity across external
GitHub publication. Recovery does not infer absence from a missing response.
Repository workflow publication is no longer a Hub transaction exception.

SDK execution commits its intent before worker I/O and conditionally applies a
response under its lease/revision. Retired bridge observation can use an already-recorded
resume identity, but cannot create a fresh resume effect. Scheduling coordinates due-job selection in its
own transaction; maintenance uses persisted cursors for its selected diagnostic
and provider-session work. Their exact boundaries belong to
`CAP-SDK-task-flow-execution`, `CAP-SDK-existing-pr-bridge` and
`CAP-EXEC-scheduling-maintenance`.

The enforcing regressions include
[PR observation fences](../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py),
activity-claim recovery tests,
[SDK late-result fences](../../modules/hub/tests/integration/features/execution/flows/test_host.py)
and [maintenance cursors](../../modules/hub/tests/integration/features/execution/maintenance/test_fairness.py).
PostgreSQL contention assertions require PostgreSQL rather than a skipped SQLite case.

## Authority belongs to its subject

Authentication establishes a caller; an operation still needs its own authority.
Browser account approval, machine scopes, direct-PR ready status, proposal
acceptance and SDK approval do not authorize one another.
`CAP-ACCESS-authentication-authorization` and `CAP-MCP-tool-access` own entrypoint
access. `CAP-PR-operator-decisions` and `CAP-SDK-task-flow-execution` own current
Run/flow input. `CAP-SDD-workflow-control` and `CAP-SDK-existing-pr-bridge`
identify retired authority rather than additional live approval subjects.

Repository workflow records are the repository/agent's responsibility and do
not create Hub authority. Descriptive activity context never grants merge or
releases a retained owner. Generic saved answers remain distinct from explicit resume. A diagnostic candidate's ancestry can justify
quarantine without granting permission to edit, close or delete it.

Source anchors are [PR controls](../../modules/hub/app/features/project_management/pipeline_runs/usecases/control.py),
[activity boundary](../../modules/hub/app/features/project_management/sdd/execution.py),
[SDK approval persistence](../../modules/hub/app/features/execution/flows/services.py)
and [connection guards](../../modules/hub/app/features/project_management/connection_tests/guards.py).

## Credential and process boundaries

Connected repositories execute their setup and internal workflow outside Hub.
Hub does not install their tools, restore assets or evaluate repository code.
GitHub credentials remain in host-controlled API publication and observation;
they are not supplied to a repository evaluator. `CAP-SDD-native-delivery`
owns this responsibility boundary.

Configured SDK HTTP workers remain a separate trust boundary. The host calls
approved addresses and resolves configured credential-variable names. Registration
does not deploy worker code. `CAP-SDK-task-flow-execution` owns that protocol;
operational configuration belongs in [execution targets](../operations/execution-targets.md).

## Errors, correlation and bounded disclosure

Failure presentation follows its boundary. SDK API failures expose `code` and
`message`; existing project REST failures expose `detail`; MCP transport and SDK workers
retain their own diagnostic contracts. There is no universal error payload
inferred from the fact that these surfaces share a service.

Scheduler jobs retain declared operator-safe messages or a generic error with a
request ID; arbitrary exception details remain in server logs. The operator-safe
formatter truncates its selected message rather than copying an unlimited
upstream response. This protects that persisted/operator-facing field, not every
log sink. `CAP-EXEC-scheduling-maintenance` owns the rule.

The Uvicorn filter removes the Google callback's authorization query while
preserving ordinary request queries. This boundary belongs to
`CAP-ACCESS-authentication-authorization`; it is not a blanket log sanitizer.

Implementation anchors are [API handlers](../../modules/hub/app/main.py),
[scheduler errors](../../modules/hub/app/features/execution/dispatchers/services.py),
[callback logging](../../modules/hub/app/access_logging.py).
This synthesis records inspected implementation and tests, not a new live
provider run, disclosure audit or production deployment.
