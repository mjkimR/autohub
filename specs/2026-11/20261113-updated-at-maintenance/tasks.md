---
id: TASKS-updated-at-maintenance
spec: SPEC-updated-at-maintenance
plan: PLAN-updated-at-maintenance
---

# Timestamp maintenance tasks

- [ ] **Task 1**: Maintain mapped timestamps and inventory every Hub owner, with service/Core and historical-row regression coverage.
  - **_Boundary**: `modules/hub/app/common/`, `modules/hub/app/features/`, `modules/hub/tests/integration/common/`
  - _Requirements: AC-01, AC-02, AC-06_
  - **Verification**: focused common timestamp integration tests on SQLite and PostgreSQL.
- [ ] **Task 2**: Preserve explicit bookkeeping exceptions and verify owed, terminal retention and observation rotation owner paths.
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/repos.py`, `modules/hub/app/features/project_management/connection_tests/repos.py`, `modules/hub/tests/integration/features/`
  - _Requirements: AC-03, AC-04, AC-05_
  - **Verification**: focused timestamp-owner, retention and owed-item tests on SQLite and PostgreSQL.
