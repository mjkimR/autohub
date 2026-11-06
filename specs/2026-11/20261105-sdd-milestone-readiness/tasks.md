---
id: TASKS-sdd-milestone-readiness
spec: SPEC-sdd-milestone-readiness
plan: PLAN-sdd-milestone-readiness
---

# Task Breakdown: SPEC-sdd-milestone-readiness

- [x] **Task 1**: Pinned bounded preview API, shared admission, graph and read-only evidence with backend tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/`, `modules/hub/app/features/project_management/repositories/`, `modules/hub/tests/integration/features/project_management/sdd/`, `modules/hub/tests/unit/features/project_management/sdd/`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-08_
  - **Verification**: Focused backend preview/start suites and real isolated SDD contracts.
- [x] **Task 2**: Preview panel, ephemeral eligible-only subset order, typed client and UI coverage
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/repositories/`, `modules/hub-ui/src/lib/api/`
  - _Requirements: AC-01, AC-02, AC-06, AC-07, AC-08_
  - **Verification**: UI preview/start/Roadmap suites, `just check-ui-api`, `just check`, `just lint-check`.
