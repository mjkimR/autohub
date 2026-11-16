---
id: PLAN-tick-continuation
spec: SPEC-tick-continuation
---

# Technical Plan: `SPEC-tick-continuation`

## 1. Constitution & Invariant Review

No architectural invariant changes. Durable intents precede I/O; existing approval, idempotency, lease and revision boundaries hold.
The once-per-tick SDK implementation detail in `CAP-SDK-task-flow-execution` changes to bounded continuation.

## 2. Architecture Overview & Impact

Keep single-advance semantics for recovery callers. Add bounded continuation to FlowWorker for maintenance.
After each committed advance, continue only active, due work; release/reclaim leases and re-read state at every transition.
SDD start invokes a best-effort ordinary advancement after the claim is bound. PR resume does so after its receipt commits.
Project queue admission is checked atomically under the project lock in prepare_implementation so prompt calls cannot bypass tick admission.
No API schema or storage migration is needed.

## 5. Error Handling & Edge Cases

A 20-second SDK timeout leaves durable work for the next tick and releases its lease.
A 10-second prompt timeout or refusal never changes a committed SDD claim into uncertain publication.
Pending external results retain the five-second minimum, approvals retain their deadlines and concurrent commands retain fencing.
Owned intervals advance from their retained due instant; missed intervals coalesce into one execution.

## 6. Verification & Test Plan

AC-01/02: flow host integration and bounded continuation regressions, including same-ID recovery, waits, cancellation and budgets.
AC-03: prompt advancement unit tests, SDD integration and project queue capacity tests.
AC-04: dispatcher cadence unit tests for jitter, missed intervals, cron and operator schedules.
Run affected SQLite suites, PostgreSQL concurrency coverage when available, just lint, just check and docs checks.
