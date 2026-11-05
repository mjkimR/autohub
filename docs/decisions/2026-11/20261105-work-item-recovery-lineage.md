---
id: ADR-work-item-recovery-lineage
title: Preserve Work Item recovery lineage
summary: "For Work Item recovery, we retain the Item and PR run with append-only recovery records, to preserve request identity and budget history, accepting stricter recovery eligibility."
proposal: SPEC-work-item-retry
status: accepted
created_at: 2026-11-05
---

# [ADR-work-item-recovery-lineage] Preserve Work Item recovery lineage

- **Status**: Accepted
- **Date**: 2026-11-05

---

## 1. Context & Problem Statement

A Work Item has one linked PR run. Replacing that link on retry would separate
the work from its request history and per-run budgets. Recovery must retain old
failures while the Item's current result advances.

## 2. Decision Drivers

- Preserve successful predecessors and original dependency meaning.
- Reconcile uncertain external work before any fresh request.
- Keep PR ownership and automatic attempt budgets in one Run.
- Make response-loss recovery and prior outcomes inspectable.

## 3. Considered Options

- Retain Item and Run with typed recovery records and immutable events: adds schema but preserves one execution lineage.
- Replace Runs and collect their history: needs cross-run budget accounting and a second identity ledger.
- Use only Plan activity: less schema but no typed recovery lifecycle or durable serialization boundary.

## 4. Decision Outcome

- Recovery retains the original Item, branch/PR identity and linked Run; a terminal Run is reactivated only through its guarded owner method. → `CAP-WORK-work-plan-execution` rule 32 Recovery ownership (MUST).
- Recovery snapshots prior outcomes and appends reconciliation/result events without replacing previous execution evidence. → `CAP-WORK-work-plan-execution` rule 30 Recovery history (MUST).
- Recovery keeps prior request identities and counters; uncertain outcomes are reconciled and exhausted automatic budgets prevent fresh dispatch. → `CAP-PR-pull-request-delivery` rules 23–24 Guarded terminal recovery and Recovery budget retention (MUST).
- Typed recovery records carry request uniqueness and lease generation alongside existing PR delivery intents. → `ARCH-06-execution` Work Item recovery lease/fencing and compatible locking rules (MUST).

## 5. Consequences

The additive migration needs no synthetic legacy recovery history. Closed,
foreign, missing and exhausted execution stays refused until a separately
supported action repairs the cause. This limits automatic recovery in exchange
for keeping request and budget ownership verifiable. No replacement Run or PR
reopening path is introduced.

## 6. Confirmation

`modules/hub/tests/integration/features/project_management/work_plans/test_item_recovery.py` checks request/history atomicity, retained Item/Run identity, budget/lease fences and successful-history retention. `modules/hub/tests/integration/features/project_management/pipeline_runs/test_work_item_terminal_recovery.py` executes the ordinary-enrollment race with PostgreSQL and verifies zero losing deliveries. The additive migration test verifies legacy rows, uniqueness and real writes after upgrade.

Executed checks and the same-head disabled/enabled invariant measurement are retained in `docs/materials/2026-11/20261105-work-item-retry/development-checks.md`. Code review and independent reconciliation check the restating contract IDs and reciprocal use-case/UX links. These checks establish fixture behavior; no live provider or deployment claim is made.
