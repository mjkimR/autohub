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

- Recovery retains the original Item, branch/PR identity and linked Run; a terminal Run is reactivated only through its guarded owner method. → `CAP-WORK-work-plan-execution` recovery ownership (MUST).
- Recovery snapshots prior outcomes and appends reconciliation/result events without replacing previous execution evidence. → `CAP-WORK-work-plan-execution` recovery history (MUST).
- Recovery keeps prior request identities and counters; uncertain outcomes are reconciled and exhausted automatic budgets prevent fresh dispatch. → `CAP-PR-pull-request-delivery` Work Item recovery (MUST).
- Typed recovery records carry request uniqueness and lease generation alongside existing PR delivery intents. → `ARCH-06-execution` recovery structure (MUST).

## 5. Consequences

The additive migration needs no synthetic legacy recovery history. Closed,
foreign, missing and exhausted execution stays refused until a separately
supported action repairs the cause. This limits automatic recovery in exchange
for keeping request and budget ownership verifiable. No replacement Run or PR
reopening path is introduced.

## 6. Confirmation

Development adds recovery integration tests under
`modules/hub/tests/integration/features/project_management/work_plans/` and
PR-owner tests under `modules/hub/tests/unit/features/project_management/`.
Review confirms reciprocal use-case/UX citations and the capability/architecture
restatements above. Tests are planned here; no implementation check is claimed.
