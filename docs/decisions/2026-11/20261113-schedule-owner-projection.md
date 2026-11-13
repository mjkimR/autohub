---
id: ADR-schedule-owner-projection
title: Derive schedule ownership from existing owners
summary: "For schedule reads spanning project and scheduler owners, we derive ownership and generic mutation permissions from existing relations, to avoid duplicate write invariants, accepting bounded read-time lookups."
proposal: SPEC-schedule-config-ownership
status: accepted
created_at: 2026-11-13
---

# [ADR-schedule-owner-projection] Derive schedule ownership from existing owners

## 1. Context & Problem Statement

Schedule configuration ownership already exists in project payloads and agent/test relationships. The generic
screen guesses owners and sometimes exposes actions the backend refuses. A read projection and a project filter
need the same ownership semantics while preserving the existing generic mutation authority.

## 2. Decision Drivers

- Keep one authoritative owner relationship without synchronizing another persisted copy.
- Keep pagination/counting and owner facts equivalent across SQLite and PostgreSQL.
- Keep request work bounded and inside the existing caller-owned database session.
- Distinguish ownership/navigation from generic mutation permission.

## 3. Considered Options

1. Derived read projection: reuse existing ownership and add bounded lookup/filter logic; no migration, with extra
   read queries and explicit malformed-reference handling.
2. Persist owner columns: simplify common reads but require backfill and every owner writer to maintain redundant
   state, while retained malformed references still require an unresolved policy. This is unnecessary for the
   requested read/navigation contract.
3. Keep browser derivation: retains all-project scans and cannot resolve agent owners or older connection tests
   beyond the separate API's bounded history; it does not satisfy the requested outcome.

## 4. Decision Outcome

- Schedule reads derive owner kind and verified owner/project IDs from existing task/payload relationships, with
  unresolved references represented as null IDs. → `CAP-EXEC-scheduling-maintenance` Interfaces & Data Contracts (MUST).
- A separate read-only generic mutation flag reflects the existing server guard, preserving editable observation
  and operator rows and protected reserved/agent-owned rows. → `CAP-EXEC-scheduling-maintenance` Interfaces & Data Contracts (MUST).
- Project filtering precedes pagination/counting and uses the same ownership precedence as returned metadata.
  → `CAP-EXEC-scheduling-maintenance` Interfaces & Data Contracts (MUST).
- Counted list reads use at most five SQL statements and one request connection with bounded page lookups.
  → `CAP-EXEC-scheduling-maintenance` Interfaces & Data Contracts (MUST).

## 5. Consequences

Owner writer paths and stored rows remain unchanged. Read-time queries must handle JSON UUID text without unsafe
casts and preserve filter/projection parity. Query-budget tests make a per-row lookup regression visible.
Future evidence that these bounded reads are insufficient can motivate a separate storage decision; no such
measurement is claimed by Planning.

## 6. Confirmation

OWNER-01 through OWNER-07 in `SPEC-schedule-config-ownership` define the acceptance examples. Development extends
schedule-config HTTP tests and the existing dispatch/agent-schedule authority suites. It checks UUID parity and the
query/connection budget on SQLite and PostgreSQL, then verifies both UI consumers. Planning inspected source and
tests; it did not run these product checks. Restating clauses are drafted in `target-docs.md` for Development.
