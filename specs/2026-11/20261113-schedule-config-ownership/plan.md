---
id: PLAN-schedule-config-ownership
spec: SPEC-schedule-config-ownership
---

# Plan: `SPEC-schedule-config-ownership`

## 1. Constitution & Invariant Review

No invariant change. `ADR-schedule-owner-projection` is accepted. Keep Router → UseCase → Service → Repository and one caller transaction. Reuse existing feature dependencies; a new edge returns to Host.

## 2. Architecture Overview & Impact

A pure owner policy defines reserved task kinds and mutation permission. A repository resolves agent/test/project rows in at most three batches. A service assembles typed reads. CRUD use cases project models inside their existing transaction; routers remain query-free. A correlated existence filter applies before repository count/page selection.

UI uses server metadata for badges, exact verified links and action visibility. Project options are an independently retryable read. Project Automation requests project_id and partitions owner kinds.

## 3. Component & Interface Design

`ScheduleConfigRead.owner` has kind, nullable project_id and object_id. `generic_mutation_allowed` is read-only. Schema inputs are unchanged. GET /schedule_configs accepts optional UUID project_id.

Count/page plus agent/test/project batches use at most five SQL statements. JSON IDs are compared as quoted canonical/hex strings; no malformed value reaches a UUID cast. Detail and mutation reads reuse the projector with one row.

## 4. Storage & State Management

No migration or backfill. Owner metadata is derived each read; the page query retains count/pagination behavior. UI preserves selected project through option-load failures.

## 5. Error Handling & Edge Cases

Malformed/dangling/nonstring owner references yield null verified IDs. Reserved protection is independent of owner resolution. Invalid query UUID uses FastAPI 422; unknown UUID is an empty counted page. Unlinked provider tasks are operator-owned.

## 6. Verification & Test Plan

AC-01/02/03/05/06 use HTTP SQLite and PostgreSQL owner/filter/budget tests, with sizes1/50, retained tests beyond30, UUID shapes and skip_count. AC-04/07 use generic-list and project-Automation integration tests. Run just gen-ui-api/check-ui-api, full just lint/check, focused and full backend/frontend coverage, independent code review and separate reconcile review. Bounds are acceptance measurements on the implementation, not a claimed baseline speedup.
