---
id: TASKS-run-origin-links
spec: SPEC-run-origin-links
plan: PLAN-run-origin-links
---

# Task Breakdown: Run origin links and subject deep links

- [ ] **Task 1**: Add bounded origin projection to all run DTO reads, with database and HTTP regressions
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/`, `modules/hub/app/features/project_management/sdd/`, `modules/hub/tests/`, `modules/hub-ui/src/lib/api/`
  - _Requirements: AC-01, AC-02, AC-03_
  - **Verification**: SQLite and PostgreSQL origin/read tests; just gen-ui-api; just check-ui-api
- [ ] **Task 2**: Render exact retained-origin links and recovery IDs without browser owner scans
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/`, `modules/hub-ui/src/lib/features/attention/owed-links.ts`, `modules/hub-ui/src/lib/features/attention/owed-links.test.ts`
  - _Requirements: AC-04, AC-06_
  - **Verification**: run page/list and owed-link Vitest regressions
- [ ] **Task 3**: Implement validated Repository unit/ref selection and independent retained batch addressing
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/repositories/`, `modules/hub-ui/src/lib/features/project-management/projects/`, `modules/hub-ui/src/routes/projects/`
  - _Requirements: AC-05, AC-06, AC-07, AC-08, AC-09_
  - **Verification**: Repository route and batch integration/state tests; just lint; just check
