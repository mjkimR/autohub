---
id: PLAN-work-item-retry
spec: SPEC-work-item-retry
---

# Technical Plan: `SPEC-work-item-retry`

## 1. Constitution & Invariant Review

`ADR-work-item-recovery-lineage` authorizes the guarded terminal transition. Ordinary Run resume keeps its existing meaning. No new dependency edge is required. Successful Item evidence and original-target merge remain authoritative.

## 2. Architecture Overview & Impact

Work Plan API → recovery use case → recovery service/repository and PR-owner recovery method. Add typed recovery/event tables and an additive migration. Existing ticks drive reconciliation and admission. The UI uses generated Work Plan resources and an inline recovery disclosure.

## 3. Component & Interface Design

```mermaid
flowchart LR
  API[Work Plan recovery API] --> Intent[Durable recovery intent]
  Intent --> Tick[Existing Work Plan tick]
  Tick --> Reconcile[Read original remote identity]
  Reconcile --> Gates[Shared admission gates]
  Gates --> Owner[Guarded PR owner]
  Owner --> CI[Existing delivery and merge flow]
```

Normative input: `POST /{plan_id}/items/{item_id}/recover` accepts UUID `request_id`, integer `expected_revision >= 1`, optional `expected_run_revision >= 1` required for linked Runs, and trimmed `reason` of 1–500 characters. Output retains recovery record and current Item. `GET /{plan_id}/items/{item_id}/recoveries` pages records/events with offset/limit. Item reads include eligibility, reason, next action, Run revision and pending recovery status. Project access applies before replay; project lock serializes request uniqueness. Replay precedes revision rejection.

## 4. Storage & State Management

Immutable recovery command/snapshot rows plus append-only typed outcome events preserve history separately from mutable current Item state. A partial unique pending index gives one recovery owner per Item. Events record accepted, reconciling, awaiting-admission, running, completed and refused transitions. Run identity is a snapshot rather than a deleting FK. Legacy Items need no backfill.

Lock order is Project → Plan → Run → Item → catalog when terminal admission needs it → recovery. Ordinary preparation admission locks Project → Plan → catalog without locking Runs. Existing observation/retention uses Run → Item and never acquires Project/Plan afterward. Existing delivery also locks Run before catalog. Item-only lease writes acquire no parent afterward. A recovery intent commits before I/O. Applying observations rechecks Plan revision/state, Run revision, Item lease token/expiry and recovery identity. No transaction holds locks during remote I/O. Pause/revoke after recovery acceptance fences activation rather than silently activating the Plan.

Historical `started_at` remains set while recovered preparation waits, preserving the existing specification-edit fence. The admission selector distinguishes this waiting state from observation. A fresh recovery delivery consumes the retained retry allowance; ordinary subsequent CI-fix attempts keep their existing per-attempt silent watchdog allowance. Recovery-confirmed final merge calls the ordinary Plan completion and mirror reflection inside the same transaction.

## 5. Error Handling & Edge Cases

Preflight refusals return 409 without history or capacity reservation. Accepted uncertain observations remain pending and retry on ticks. Definitive accepted refusals append a refused event and release ownership. Active-owner uniqueness failure is translated to a conflict with zero dispatch. Terminal recovery preserves epoch and attempt numbering; fresh delivery is allowed only after definitive prior stop and existing budgets. Pushed-head/external implementation evidence resumes CI without delivery. Original correctly merged PR records success without budget use.

## 6. Verification & Test Plan

Task tests map to every scenario. Use SQLite integration tests for deterministic identity/history/rollback and mocked external effects; execute PostgreSQL lock/race and additive migration checks with actual Docker/testcontainers. UI integration tests cover confirmation, history and response-loss identity. Regenerate API with `just gen-ui-api`; run `just check-ui-api`, `just lint`, `just check` and `just docs-check`.

Compare identical controlled failed-chain fixtures with recovery disabled/enabled: successful predecessor writes, Run count, epoch and fresh delivery counts. Record method and observed counts rather than claim latency improvement. Required cases include Plan/Run stale revisions, pause/revoke in each phase, lease expiry, unreadable remote state, uncertain delivery, capacity, exhausted epoch, competing owner and retention.
