---
id: TASKS-pending-decision-count
spec: SPEC-pending-decision-count
plan: PLAN-pending-decision-count
---

# Task Breakdown: `SPEC-pending-decision-count` Exact pending-decision count

## Phase 1: Backend count

- [x] **Task 1.1**: Exact actionable count on the decision list, with integration tests
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/discovery_schemas.py`, `modules/hub/app/features/project_management/pipeline_runs/discovery_repo.py`, `modules/hub/app/features/project_management/pipeline_runs/discovery_service.py`, `modules/hub/app/features/project_management/pipeline_runs/usecases/discovery.py`, `modules/hub/tests/integration/features/project_management/pipeline_runs/test_discovery.py`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: `just test tests/integration/features/project_management/pipeline_runs/test_discovery.py tests/integration/mcp`, `just test-pg tests/integration/features/project_management/pipeline_runs/test_discovery.py`

## Phase 2: Typed client and shell

- [x] **Task 2.1**: Regenerate the typed client
  - **_Boundary**: `modules/hub-ui/src/lib/api/generated/`
  - _Requirements: AC-07_
  - **Verification**: `just gen-ui-api`, `just check-ui-api`
- [x] **Task 2.2**: Shell shows the exact count, with unit and integration tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/pending-decisions.svelte.ts`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/pending-decisions.test.ts`, `modules/hub-ui/src/lib/components/shared/AppShell.svelte`, `modules/hub-ui/src/lib/components/shared/AppShell.integration.test.ts`
  - _Requirements: AC-05, AC-06_
  - **Verification**: `just test-ui`, `just check hub-ui`, `just lint`
