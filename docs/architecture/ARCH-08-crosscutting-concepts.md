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
(`CAP-PR-agent-dispatch`). Proposal publication records its candidate commit and
later reconciles that exact pushed identity (`CAP-SDD-native-delivery`). SDK
workers inspect the existing attempt before any authorized resubmission
(`CAP-SDK-task-flow-execution`); the PR bridge also reuses the existing owner's
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
[proposal publication](../../modules/hub/app/features/project_management/sdd/plan_publication.py),
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

Proposal publication deliberately differs: its final authorization and bounded
push hold Run and Project row locks together. Cancellation and project changes
linearize before or after that push. The push remains outside the isolated
repository command context, under its explicit publication/credential boundary.
`CAP-SDD-native-delivery` owns this exception; it is not a reason to hold ordinary
observation locks across provider or CI waits.

SDK execution commits its intent before worker I/O and conditionally applies a
response under its lease/revision. The bridge guards its claim and records the
resume identity independently. Scheduling coordinates due-job selection in its
own transaction; maintenance uses persisted cursors for its selected diagnostic
and provider-session work. Their exact boundaries belong to
`CAP-SDK-task-flow-execution`, `CAP-SDK-existing-pr-bridge` and
`CAP-EXEC-scheduling-maintenance`.

The enforcing regressions include
[PR observation fences](../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py),
[publication/cancel ordering](../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py),
[SDK late-result fences](../../modules/hub/tests/integration/features/execution/flows/test_host.py)
and [maintenance cursors](../../modules/hub/tests/integration/features/execution/maintenance/test_fairness.py).
PostgreSQL contention assertions require PostgreSQL rather than a skipped SQLite case.

## Authority belongs to its subject

Authentication establishes a caller; an operation still needs its own authority.
Browser account approval, machine scopes, direct-PR ready status, proposal
acceptance and SDK approval do not authorize one another.
`CAP-ACCESS-authentication-authorization` and `CAP-MCP-tool-access` own entrypoint
access. `CAP-PR-operator-decisions`, `CAP-SDD-workflow-control` and
`CAP-SDK-existing-pr-bridge` own the decisions that act on delivery evidence.

Repository workflow records establish workflow progress, not an independent Hub
merge grant. Admission retains the applicable source/workflow identity so later
inspection can detect a changed contract. Generic resume remains distinct from
restoring withdrawn approval. A diagnostic candidate's ancestry can justify
quarantine without granting permission to edit, close or delete it.

Source anchors are [PR controls](../../modules/hub/app/features/project_management/pipeline_runs/usecases/control.py),
[SDD control](../../modules/hub/app/features/project_management/sdd/control.py),
[SDK approval persistence](../../modules/hub/app/features/execution/flows/services.py)
and [connection guards](../../modules/hub/app/features/project_management/connection_tests/guards.py).

## Credential and process boundaries

Repository workflow evaluation uses the runtime the evaluated commit's own
`uv.lock` pins, in OS isolation. It exposes a disposable writable checkout and
read-only tools without inherited host credentials or network access. Installing
that runtime keeps the same split: the Hub process fetches locked Git sources with
the connector's credential and installs hashed wheels, which runs no package code;
every step that runs repository build code or the new runtime's interpreter is
sandboxed without network, credentials or write access outside one directory
(`ADR-offline-source-build`). Missing isolation is a refusal, not an invitation to
run repository code directly. Git publication has a separate host-controlled
boundary that can use the connector's credential. `CAP-SDD-runtime-isolation`
owns both the runtime contract and its limits.

Configured SDK HTTP workers are a different trust boundary: the host intentionally
calls their approved addresses and resolves a configured credential-variable name
for each call. Release registration does not install worker code or grant a
caller an arbitrary checkout path. `CAP-SDK-task-flow-execution` and
`CAP-SDK-existing-pr-bridge` own these bindings; operational configuration belongs
in [execution targets](../operations/execution-targets.md).

The checks in [runtime unit tests](../../modules/hub/tests/unit/features/project_management/sdd/test_runtime.py),
[install unit tests](../../modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py),
[real CLI isolation tests](../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py)
and [real build isolation tests](../../modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py)
distinguish command construction from actual restricted file/network access.
They do not assert that the entire Hub process has no credentials or network.

## Errors, correlation and bounded disclosure

Failure presentation follows its boundary. SDK API failures expose `code` and
`message`; existing project REST failures expose `detail`; MCP transport and isolated CLI evaluation
retain their own diagnostic contracts. There is no universal error payload
inferred from the fact that these surfaces share a service.

Scheduler jobs retain declared operator-safe messages or a generic error with a
request ID; arbitrary exception details remain in server logs. The operator-safe
formatter truncates its selected message rather than copying an unlimited
upstream response. This protects that persisted/operator-facing field, not every
log sink. `CAP-EXEC-scheduling-maintenance` owns the rule.

The Uvicorn filter removes the Google callback's authorization query while
preserving ordinary request queries. SDD command errors use host-authored,
allowlisted diagnostics rather than forwarding repository stderr. These bounded
mechanisms belong to `CAP-ACCESS-authentication-authorization` and
`CAP-SDD-runtime-isolation`; they are not blanket log sanitizers.

Implementation anchors are [API handlers](../../modules/hub/app/main.py),
[scheduler errors](../../modules/hub/app/features/execution/dispatchers/services.py),
[callback logging](../../modules/hub/app/access_logging.py) and
[isolated command handling](../../modules/hub/app/features/project_management/sdd/checkout.py).
This synthesis records inspected implementation and tests, not a new live
provider run, disclosure audit or production deployment.
