---
id: ADR-sdd-batch-ledger
title: Keep sequential SDD selection separate from native activity owners
summary: "For sequential native SDD work, we retain an immutable batch ledger linked to existing activity owners, to preserve approvals and recovery, accepting explicit waits for uncertain lineage."
proposal: SPEC-sdd-milestone-execution
status: accepted
created_at: 2026-11-05
---

# [ADR-sdd-batch-ledger] Keep sequential SDD selection separate from native activity owners

## 1. Context & Problem Statement

Selected native units cross proposal Planning, handoff and spec Development. `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` assign each activity and PR its own authority. Repository anchors can disappear after handoff; a batch cannot infer scheduling authority from a similar spec name.

## 2. Decision Drivers

- Preserve one existing PR owner and its revisioned approval fences.
- Recover partial remote effects without admitting replacement work.
- Permit explicit milestone-chain intent while exposing current dependency holds.
- Keep repository scheduling and native activity admission distinct.

## 3. Considered Options

- **Separate SDD batch ledger (selected)**: records intent, claims, controls and exact lineage; existing native owners execute. Adds persistence and recovery code.
- **Work Plan reuse**: reuses batch UI/persistence but lacks bound native units and would duplicate their authority.
- **One batch PipelineRun**: simpler initial state but conflicts with one-PR binding and per-unit approvals.
- **Eligible-only selection**: reuses the predecessor's local subset exactly but cannot retain a dependency-held milestone chain. Explicit future-intent selection adds an execution-specific control without changing preview authority.

## 4. Decision Outcome

We chose a separate immutable SDD batch ledger with explicit future-intent selection.

- Batch scheduling remains an additional constraint, and existing activity owners retain workflow approvals and CI/merge. → `CAP-SDD-native-delivery` batch ownership (MUST).
- One member retains its slot until confirmed success or inspected settlement, and a durable admission claim precedes external effects. → `ARCH-06-execution` sequential admission and recovery (MUST).
- Exact completed SPEC evidence satisfies a unit prerequisite; recorded activity lineage alone does not rewrite a PROP dependency. → `CAP-SDD-native-delivery` batch dependencies (MUST).
- Pause and stop govern future claims, while admitted activities retain their own controls. → `CAP-SDD-native-delivery` batch controls (MUST).

## 5. Consequences

Operators can retain chain intent across reloads while each unready entry visibly waits. Additional reservation and retention records require PostgreSQL concurrency and crash-window tests. Unresolved canonical reference repairs stop a chain instead of guessing a successor. A changed selection requires stopping and creating another batch after admitted work settles.

## 6. Confirmation

Compliance is checked by `modules/hub/tests/integration/features/project_management/sdd/test_batches.py`, `test_batch_claims.py` and `test_batch_progression.py` beside it; `modules/hub/tests/unit/features/project_management/sdd/test_batch_activities.py` and `test_batch_evidence.py`; `modules/hub/tests/integration/features/execution/maintenance/test_sdd_batches.py`; and the repository UI batch tests. PostgreSQL multi-connection checks cover shared claims, controls and enrollment response loss. `CAP-SDD-native-delivery` sequential SDD batch contract and `ARCH-06-execution` sequential admission and recovery restate the clauses. `SPEC-sdd-milestone-execution` retains executed check results separately from source inspection; no deployment or live GitHub result is claimed.
