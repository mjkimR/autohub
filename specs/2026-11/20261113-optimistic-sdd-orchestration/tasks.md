---
id: TASKS-optimistic-sdd-orchestration
spec: SPEC-optimistic-sdd-orchestration
plan: PLAN-optimistic-sdd-orchestration
---

# Task Breakdown: `SPEC-optimistic-sdd-orchestration`

- [x] **Task 1**: Route optimistic SDD intent through ordinary PR delivery, fence legacy Runs and preserve question/head/merge control; verify API/progression and migration cases.
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/`, `modules/hub/app/features/project_management/owed_items/`, `modules/hub/app/features/project_management/work_plans/`, `modules/hub/app/features/project_management/sdd/execution.py`, `modules/hub/migrations/`, `modules/hub/tests/integration/features/project_management/pipeline_runs/`, `modules/hub/tests/integration/features/project_management/owed_items/test_owed_items.py` (scope extension: Reuse ordinary activity question fixtures after native decision retirement), `modules/hub/tests/integration/migrations/`, `modules/hub/tests/unit/features/project_management/pipeline_runs/`
  - _Requirements: AC-01, AC-02, AC-04, AC-05, AC-06, AC-07, AC-08, AC-10_
  - **Verification**: focused backend progression, migration and PostgreSQL ownership tests.
- [x] **Task 2**: Replace native activity setup with GitHub-only Draft publication, retire evaluator/batch execution, retain history/reconciliation and simplify MCP; replace evaluator tests.
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/`, `modules/hub/app/main.py` (scope extension: Expose retired SDD error codes to clients), `modules/hub/app/mcp/`, `modules/hub/app/features/execution/tasks/domains/maintenance/`, `modules/hub/tests/integration/features/project_management/sdd/`, `modules/hub/tests/integration/sdd_runtime.py` (scope extension: Remove the evaluator-only shared test environment), `modules/hub/tests/unit/features/project_management/sdd/`, `modules/hub/tests/integration/features/execution/maintenance/`, `modules/hub/tests/integration/mcp/`, `modules/hub/tests/unit/mcp/`
  - _Requirements: AC-01, AC-02, AC-03, AC-07, AC-08, AC-10_
  - **Verification**: optimistic activity ownership/recovery, history and retired API tests; app/MCP imports.
- [x] **Task 3**: Retire evaluator-coupled SDK bridge bindings and preserve receipt-backed observe-only behavior with generic SDK regressions.
  - **_Boundary**: `modules/hub/app/features/execution/flows/`, `modules/hub/tests/integration/features/execution/flows/`, `modules/hub/tests/unit/features/execution/flows/`, `packages/sdk/`
  - _Requirements: AC-07, AC-08, AC-09_
  - **Verification**: bridge retirement, generic flow and standalone SDK tests/build when SDK changes.
- [x] **Task 4**: Implement reviewed UI simplification, original-intent recovery and historical-only native surfaces; regenerate typed API and verify frontend.
  - **_Boundary**: `modules/hub-ui/src/`, `modules/hub-ui/eslint.config.js`
  - _Requirements: AC-03, AC-04, AC-05, AC-07, AC-10_
  - **Verification**: relevant UI integration tests, `just gen-ui-api`, UI lint/types/build.
- [x] **Task 5**: Remove evaluator packaging/test tooling and reconcile owning documents and partially related proposals with implemented behavior.
  - **_Boundary**: `config/`, `scripts/`, `docker/`, `.github/workflows/`, `justfile`, `modules/hub/tests/unit/scripts/test_check_devkit.py` (scope extension: Preserve root and viewer pin regressions after seed removal), `README.md`, `docs/`
  - _Requirements: AC-07, AC-11, AC-12_
  - **Verification**: packaging inspection, `just lint`, `just check`, `just docs-check`, full relevant checks.
