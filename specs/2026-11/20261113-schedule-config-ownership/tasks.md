---
id: TASKS-schedule-config-ownership
spec: SPEC-schedule-config-ownership
plan: PLAN-schedule-config-ownership
---

# Tasks: `SPEC-schedule-config-ownership`

- [ ] **Task 1**: Bounded owner projection, shared guard policy and project filter with database regressions
  - **_Boundary**: `modules/hub/app/features/scheduling/schedule_configs/`, `modules/hub/tests/integration/features/scheduling/schedule_configs/`, `modules/hub-ui/src/lib/api/`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06_
  - **Verification**: SQLite/PostgreSQL HTTP owner/filter/query-budget regressions and generated API freshness.
- [ ] **Task 2**: Owner-aware generic schedule list and project-filtered Automation loading with UI regressions
  - **_Boundary**: `modules/hub-ui/src/lib/features/scheduling/schedule-configs/`, `modules/hub-ui/src/lib/features/project-management/projects/`
  - _Requirements: AC-04, AC-05, AC-07_
  - **Verification**: UI integration tests, full lint/types/build.
