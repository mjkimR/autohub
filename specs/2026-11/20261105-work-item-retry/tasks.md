---
id: TASKS-work-item-retry
spec: SPEC-work-item-retry
plan: PLAN-work-item-retry
---

# Task Breakdown: `SPEC-work-item-retry`

## Implementation

- [x] **Task 1**: Recovery persistence, request service and API with migration and transactional tests
  - **_Boundary**: `modules/hub/app/features/project_management/work_plans/`, `modules/hub/migrations/`, `modules/hub/tests/integration/migrations/`, `modules/hub/tests/integration/features/project_management/work_plans/`
  - _Requirements: AC-03, AC-04, AC-05, AC-07, AC-11_
  - **Verification**: `just test modules/hub/tests/integration/features/project_management/work_plans/ modules/hub/tests/integration/migrations/`

- [x] **Task 2**: Fenced tick recovery and guarded terminal PR-owner activation with race tests
  - **_Boundary**: `modules/hub/app/features/project_management/work_plans/`, `modules/hub/app/features/project_management/pipeline_runs/`, `modules/hub/tests/integration/features/project_management/work_plans/`, `modules/hub/tests/integration/features/project_management/pipeline_runs/`, `modules/hub/tests/unit/features/project_management/`
  - _Requirements: AC-01, AC-02, AC-04, AC-05, AC-06, AC-08, AC-09, AC-10, AC-11_
  - **Verification**: `just test-pg modules/hub/tests/integration/features/project_management/work_plans/ modules/hub/tests/integration/features/project_management/pipeline_runs/`

- [x] **Task 3**: Recovery disclosure and typed API with UI integration tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/work-plans/`, `modules/hub-ui/src/lib/api/`
  - _Requirements: AC-12_
  - **Verification**: `just test-ui; just check-ui-api`

- [x] **Task 4**: Recovery invariant comparison and retained verification evidence
  - **_Boundary**: `docs/capabilities/work-plans/`, `docs/capabilities/delivery/CAP-PR-pull-request-delivery.md`, `docs/usecases/work-plans/`, `docs/usecases/delivery/UC-deliver-pull-request.md`, `docs/ux/work-plans/`, `docs/steering/ux-objects.md`, `docs/architecture/ARCH-06-execution.md`, `docs/decisions/2026-11/20261105-work-item-recovery-lineage.md`, `docs/materials/2026-11/20261105-work-item-retry/`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12_
  - **Verification**: `just test modules/hub/tests/integration/features/project_management/work_plans/test_item_recovery.py`; retained baseline comparison in `docs/materials/2026-11/20261105-work-item-retry/development-checks.md`

