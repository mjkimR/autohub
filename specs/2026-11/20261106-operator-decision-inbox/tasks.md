---
id: TASKS-operator-decision-inbox
spec: SPEC-operator-decision-inbox
plan: PLAN-operator-decision-inbox
---

# Task Breakdown: `SPEC-operator-decision-inbox` Find pending delivery decisions across projects

## Phase 1: Implementation

- [x] **Task 1**: Persist and transactionally maintain decision discovery with migration and owner lifecycle tests
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/`, `modules/hub/app/features/project_management/sdd/`, `modules/hub/migrations/versions/`, `modules/hub/tests/integration/migrations/`, `modules/hub/tests/integration/features/project_management/pipeline_runs/`, `modules/hub/tests/integration/features/project_management/sdd/`
  - _Requirements: AC-01, AC-02, AC-04, AC-07_
  - **Verification**: Owner integration and migration tests on SQLite and PostgreSQL.

- [x] **Task 2**: Expose bounded discovery and exact-subject refresh with cursor and concurrency tests
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/`, `modules/hub/app/features/project_management/sdd/`, `modules/hub/tests/integration/features/project_management/pipeline_runs/`, `modules/hub/tests/integration/features/project_management/sdd/`, `modules/hub-ui/src/lib/api/`
  - _Requirements: AC-01, AC-03, AC-05, AC-06, AC-07_
  - **Verification**: Listing/provider-call bounds and refreshed inspection CAS tests; regenerate typed API.

- [x] **Task 3**: Build Decisions navigation and exact owner review with UI interaction tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/`, `modules/hub-ui/src/lib/components/`, `modules/hub-ui/src/routes/`, `modules/hub-ui/src/lib/api/`, `docs/ux/sdd/UX-sdd-workflow-request.md` (Host-authorized exact selection reflection), `docs/ux/sdd/UX-sdd-run.md` (Host-authorized exact selection reflection)
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08_
  - **Verification**: UI tests cover filtering, paging, exact request review, failure, changed generations and focus restoration; `just lint` and `just check`.
