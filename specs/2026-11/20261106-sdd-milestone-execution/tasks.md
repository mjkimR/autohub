---
id: TASKS-sdd-milestone-execution
spec: SPEC-sdd-milestone-execution
plan: PLAN-sdd-milestone-execution
---

# Task Breakdown: `SPEC-sdd-milestone-execution`

## Phase 1: Implementation

- [x] **Task 1.1**: Persist immutable selection, strict creation/read/control contracts and atomic revision receipts.
  - **_Boundary**: modules/hub/app/features/project_management/sdd/, modules/hub/app/features/project_management/pipeline_runs/, modules/hub/app/features/execution/tasks/domains/maintenance/, modules/hub/migrations/, modules/hub/tests/integration/migrations/, modules/hub/tests/integration/features/execution/maintenance/, modules/hub/tests/integration/features/project_management/sdd/, modules/hub/tests/unit/features/project_management/sdd/
  - _Requirements: AC-01, AC-04, AC-07, AC-10_
  - **Verification**: SQLite and PostgreSQL selection, replay, lock race and migration tests.
- [x] **Task 1.2**: Coordinate fresh exact admission and native owner recovery, phase lineage, drift and retention through fair maintenance.
  - **_Boundary**: modules/hub/app/features/project_management/sdd/, modules/hub/app/features/project_management/pipeline_runs/, modules/hub/app/features/execution/tasks/domains/maintenance/, modules/hub/migrations/, modules/hub/tests/integration/migrations/, modules/hub/tests/integration/features/execution/maintenance/, modules/hub/tests/integration/features/project_management/sdd/, modules/hub/tests/unit/features/project_management/sdd/
  - _Requirements: AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-09, AC-10_
  - **Verification**: Dependency, phase, merge, crash-checkpoint, admission/control races and maintenance/retention regressions.
- [x] **Task 1.3**: Add durable execution selection and control UI, typed resources and owning Living Spec reflection.
  - **_Boundary**: modules/hub-ui/src/lib/api/, modules/hub-ui/src/lib/features/project-management/repositories/, modules/hub-ui/src/lib/features/project-management/pipeline-runs/, docs/capabilities/sdd/, docs/capabilities/execution/, docs/usecases/sdd/, docs/ux/sdd/, docs/steering/, docs/architecture/, docs/decisions/2026-11/20261106-sdd-batch-ledger.md
  - _Requirements: AC-01, AC-07, AC-08, AC-10_
  - **Verification**: UI selection, preferences, confirmation, stale response and exact replay tests; just lint/check and independent reconciliation.
