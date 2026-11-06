---
id: PLAN-decision-continuation
spec: SPEC-decision-continuation
---

# Technical plan for `SPEC-decision-continuation`

## 1. Constitution & Invariant Review

None. Preserve `ADR-decision-continuation-outcomes`, owner authority and replay guards.

## 2. Architecture Overview & Impact

Router → outcome use case → pure outcome service → exact owner repository. Read existing question, answer and resume records in one transaction; no external observer calls or ledger.
UI retains immutable mutation intents in memory by run and actor session, shared across close/reopen. Owner panels use the same outcome region and explicit retry control.

## 3. Component & Interface Design

`GET /api/v1/pipeline-runs/{run_id}/decision-outcomes/{request_id}?operation=question|answer|resume` returns a discriminated typed outcome with current revision/state and nullable recorded evidence. Missing scoped request returns unknown; missing run 404; invalid discriminator/UUID 422.
Answer publication uses exact validated envelope identity/question/workflow/segment and inspected head. Missing evidence remains unknown/pending.

## 4. Storage & State Management

Reuse persisted owner records and predecessor inspection evidence. No migration or durable browser payload storage. Preserve original endpoint/body across uncertainty and temporary close. An acknowledged mutation survives failed subsequent reads.

## 5. Error Handling & Edge Cases

Changed current head/authority disables old continuation; terminal work stays readable. Reads never reconcile or resume. Proposal reconciliation is a separately explained existing resume operation.

## 6. Verification & Test Plan

Integration tests cover exact namespace/run lookup, no external calls, unknown/error cases, attempt/delivery joins, native envelope publication and current authority. UI tests cover immutable retry, close/reopen, acknowledged refresh error, explicit answer selection and native channels. Run backend initialization, SQLite/PostgreSQL affected suites, UI tests, API generation, `just lint`, `just check`, rules and generated freshness.
