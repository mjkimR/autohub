---
id: TASKS-remove-sdd-compat
spec: SPEC-remove-sdd-compat
plan: PLAN-remove-sdd-compat
---

# Task Breakdown: `SPEC-remove-sdd-compat`

- [x] **Task 1**: Remove native compatibility and retain standalone activity safety, with backend regressions.
  - **_Boundary**: `modules/hub/app/features/project_management/`, `modules/hub/app/features/execution/flows/`, `modules/hub/app/features/execution/tasks/domains/maintenance/history.py`, `modules/hub/app/mcp/`, `modules/hub/migrations/`, `modules/hub/tests/`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: focused backend and migration tests; `just lint`; `just check`.
- [x] **Task 2**: Remove native UI surfaces and generated API contracts, with frontend regressions.
  - **_Boundary**: `modules/hub-ui/src/lib/`, `modules/hub-ui/eslint.config.js`
  - _Requirements: AC-01, AC-02, AC-03_
  - **Verification**: `just gen-ui-api`; `just test-ui`; `just check-ui-api`; `just check`.
- [x] **Task 3**: Reflect supported execution in the Living Spec and verify references.
  - **_Boundary**: `docs/capabilities/`, `docs/usecases/`, `docs/architecture/`, `docs/decisions/`, `docs/ux/`, `docs/steering/`, `docs/development/`, `docs/operations/`, `docs/materials/`, `README.md`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: `just docs-check`; current contract/source comparison.
