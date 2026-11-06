---
id: TASKS-work-item-replacement
spec: SPEC-work-item-replacement
plan: PLAN-work-item-replacement
---
# Task breakdown: `SPEC-work-item-replacement`

- [ ] **Task 1**: Persist and validate replacement evidence and request identity.
  - _Boundary:_ modules/hub/app/features/project_management/work_plans/, modules/hub/migrations/, modules/hub/tests/integration/migrations/, modules/hub/tests/integration/features/project_management/work_plans/, modules/hub/tests/unit/features/project_management/
  - _Requirements: AC-01, AC-02, AC-03, AC-05, AC-07, AC-08_
  - Verification: replacement API, replay, retention and migration tests.
- [ ] **Task 2**: Consume exact-edge acceptance under existing admission and edit fences.
  - _Boundary:_ modules/hub/app/features/project_management/work_plans/, modules/hub/tests/integration/features/project_management/work_plans/, modules/hub/tests/unit/features/project_management/
  - _Requirements: AC-01, AC-04, AC-06, AC-08_
  - Verification: ordinary baseline, one-edge release and PostgreSQL concurrent controls/withdrawal/admission/recovery tests.
- [ ] **Task 3**: Implement review UI and reconcile owning contracts.
  - _Boundary:_ modules/hub-ui/src/lib/api/, modules/hub-ui/src/lib/features/project-management/work-plans/, docs/capabilities/work-plans/, docs/usecases/work-plans/, docs/ux/work-plans/, docs/steering/, docs/architecture/
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08_
  - Verification: UI integration tests, API generation, lint/type/build and independent reconciliation.
