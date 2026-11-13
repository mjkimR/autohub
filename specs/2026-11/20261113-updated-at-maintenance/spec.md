---
id: SPEC-updated-at-maintenance
title: Maintain updated_at on every owner write
summary: Maintain updated_at for Hub ORM and SQLAlchemy Core writes, preserve explicit owner exceptions, and correct last-write readers without reconstructing historical timestamps.
status: completed
created: 2026-11-13
related_capabilities: [CAP-PR-owed-items, CAP-EXEC-scheduling-maintenance, CAP-WORK-work-plan-execution]
related_usecases: []
workflow: sdd-spec-bugfix
---

# [SPEC-updated-at-maintenance] Maintain updated_at on every owner write

## 1. Problem Statement & Motivation

Hub timestamp-bearing models inherit a server-onupdate marker without an UPDATE generator. Ordinary owner writes leave `updated_at` at creation time, violating the last-write basis of `CAP-PR-owed-items`, `CAP-EXEC-scheduling-maintenance` and `CAP-WORK-work-plan-execution`.

## 2. Defect Characterization

- **Current behavior**: an ORM configuration update changes its data without advancing its stored update time. Mapped Core owner writes have the same gap unless they assign an explicit timestamp.
- **Expected behavior and its basis**: ordinary persisted owner writes maintain UTC last-write timestamps; owed and retention readers use that saved value.
- **Behavior to preserve**: explicit flow/connection-step business clocks; notification marks and pure run/connection-test lease claims preserve the prior time. Run lease release retains its observation rotation clock.
- **Reproduction conditions**: focused integration test writes a configuration through its service at a controlled later clock, without assigning the expected timestamp. Metadata inventory also exposes missing onupdate policies.

## 3. Non-Goals

1. **Scope Excluded**: schema changes, triggers, historical backfill, upstream dependency changes, raw SQL timestamp guarantees and state-entry clocks.
2. **Scope Excluded**: frontend/SDK changes, new retention windows or new owed kinds.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] ORM owner timestamp maintenance
- **Given** a saved configuration and Hub timestamp model inventory
- **When** its service persists changed data at a controlled later UTC instant
- **Then** updated_at records that instant, created_at stays fixed, and every Hub timestamp model has the local policy.

### [AC-02] Core updates and explicit clocks
- **Given** mapped owner rows on SQLite or PostgreSQL
- **When** Core writes omit or explicitly supply updated_at
- **Then** omitted timestamps advance and explicit timestamps or same-column preservation expressions win.

### [AC-03] Owed-owner last-write reads
- **Given** stopped/failed runs, proposed Plans, attention Items and replacement links
- **When** actual owner writes change persisted state
- **Then** owed reads use the saved updated_at without fixtures assigning the expected result; unchanged ORM flushes and rejected writes preserve timestamps.

### [AC-04] Terminal readers and retention
- **Given** an old run that becomes terminal through its operator or webhook owner
- **When** finish and retention readers inspect it
- **Then** they use its maintained transition write time and do not expire it solely because creation was over 30 days earlier.

### [AC-05] Bookkeeping and observation rotation
- **Given** a run or connection test with a stored timestamp
- **When** notification marks, run lease acquisition/renewal or connection-test claim occur
- **Then** updated_at stays unchanged; run lease release still advances its observation timestamp and rotates a population above the selection bound; mixed business writes advance.

### [AC-06] Historical rows
- **Given** a preexisting row with historical timestamps
- **When** it is read or flushed unchanged
- **Then** its timestamps remain unchanged until its next non-exempt write; no backfill or trigger is installed.

### [AC-07] Mutation replay read consistency
- **Given** ordinary run resume or retired SDD run acknowledgment and its exact replay
- **When** maintained timestamps are returned on SQLite or PostgreSQL
- **Then** first response and replay preserve identical persisted timestamp serialization without restarting execution.

## Source feedback

- `FB-timestamp-updated-at-never-maintained`: received in full. The inherited claim about the sole explicit writer is corrected by the carried evidence inventory, which includes lease release and connection-test step writers.
