# Durable SDK task/flow host

Status: completed (locally verified; not deployed). Implements workbench F2 after the SDK/mock contract slice.

## Scope

Serve SDK release/activation/run/command APIs from the actual Auto Hub backend.
Persist provider ownership, immutable release/binding snapshots, runs, steps,
attempt intents, and command receipts. Advance bounded work through system
maintenance using DB leases and revision fencing, outside-transaction worker
I/O. Support native identity and explicitly configured HTTP executors.

## Acceptance criteria

- AC-01: SDK registration, activation CAS, same-ID/content replay and conflicts,
  request/command replay and content conflicts work against real database APIs.
- AC-02: Same machine owns a provider/environment across key rotation; read,
  write and approval scopes are checked. Foreign namespace/run access fails.
  Approval commands record an authenticated actor and target revision.
- AC-03: Run inputs and release/resolved binding snapshots survive fresh app,
  session, worker and engine instances; active release changes do not mutate runs.
- AC-04: Ordered tasks, approval deadline, bounded revise and explicit task
  resume work with schema validation and cumulative attempt budgets. GET is
  read-only; scheduler ticks advance durable conditions.
- AC-05: An intent is committed before external I/O. Lost response/process death
  reconciles the same attempt ID. Unknown results never create a new attempt.
  Worker result application requires an unexpired lease and unchanged revision.
- AC-06: Concurrent workers, same-key submissions, commands and expired-lease
  reclamation are covered against PostgreSQL. No DB locks span network calls.
- AC-07: Cancel acknowledgment differs from worker termination. HTTP cancellation
  requires terminal evidence/tombstones; late results cannot advance a canceled
  or superseded run. Missing/unavailable worker configuration remains recoverable.
- AC-08: Migration upgrade/downgrade matches model metadata, UI API declarations
  are regenerated, backend suite and required lint/check pass.

## Non-goals

No planhub UI/backend planning integration, PR/GitHub/specrig adapter, generic DAG,
code upload, arbitrary internal scheduler task execution, deployment or SDK release
publication. Generic approval is a scoped machine command, not PR approval evidence.
