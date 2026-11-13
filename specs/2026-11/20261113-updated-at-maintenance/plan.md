---
id: PLAN-updated-at-maintenance
spec: SPEC-updated-at-maintenance
---

# Timestamp maintenance plan

## 1. Constitution & Invariant Review

No invariant change. Preserve `ARCH-02-constraints` transaction ownership and SDK isolation. The accepted local mixin repair needs no ADR or migration.

## 2. Architecture Overview & Impact

A Hub-owned TimestampMixin subclasses the pinned framework mixin and overrides only updated_at with its existing UTC column/default shape plus callable onupdate. Every Hub model imports that policy. Repositories preserve the accepted bookkeeping exceptions explicitly; lease release keeps its caller clock for observation fairness. No new dependency edge is introduced. Retain the inherited server-onupdate marker alongside the callable.

AC-07 preserves existing ordinary resume and SDD acknowledgment replay consistency: refresh the changed run after flush before serializing, so SQLite uses the same persisted timestamp representation on first response and replay. The Host explicitly authorized these exact necessary owner-read repairs after full-suite evidence; it adds no timestamp representation redesign.

## 4. Storage & State Management

SQLAlchemy mapped ORM/Core updates generate a UTC value when updated_at is omitted. Explicit business values win. Raw SQL and reflected tables are outside this policy. Existing rows remain untouched on startup/read; their next business write obtains the maintained time. Owed waiting_since is last-write evidence, not state-entry duration.

## 6. Verification & Test Plan

AC-01/02/06: common timestamp inventory and configuration service/Core regressions with controlled clocks, unchanged reads/flushes and explicit overrides.
AC-03/04: owner-path owed/terminal retention regressions without assigning expected timestamps.
AC-05: run leases/announcement, connection-test claim/finish and bounded observation rotation regressions.
Run focused SQLite and PostgreSQL tests, `just lint`, `just check`, document rules and mandatory independent code and reconciliation review. Keep Red reproduction as regression coverage.
