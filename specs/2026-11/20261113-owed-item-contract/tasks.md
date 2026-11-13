---
id: TASKS-owed-item-contract
spec: SPEC-owed-item-contract
plan: PLAN-owed-item-contract
---

# Task Breakdown: `SPEC-owed-item-contract` Owed item contract for operator debt

## Phase 1: Backend contract

- [ ] **Task 1.1**: Owed-item aggregate read (schemas, repository, service, use case, router)
  - **_Boundary**: modules/hub/app/features/project_management/owed_items/, modules/hub/tests/integration/features/project_management/owed_items/, modules/hub/app/router.py (scope extension: registers the owed-items router under the authenticated v1 API so the owed reads of AC-01 and AC-10 are reachable)
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11_
  - **Verification**: `just test modules/hub/tests/integration/features/project_management/owed_items` and the same path with `just test-pg`
- [ ] **Task 1.2**: Per-run pending-decision flag on `PipelineRunRead`
  - **_Boundary**: modules/hub/app/features/project_management/pipeline_runs/, modules/hub/tests/integration/features/project_management/pipeline_runs/
  - _Requirements: AC-12_
  - **Verification**: `just test modules/hub/tests/integration/features/project_management/pipeline_runs`

## Phase 2: Typed client and Living Spec

- [ ] **Task 2.1**: Regenerate the typed client and check layering
  - **_Boundary**: modules/hub-ui/src/lib/api/
  - _Requirements: AC-13_
  - **Verification**: `just gen-ui-api`, `just check-ui-api`, `uv run devkit rules check`
- [ ] **Task 2.2**: Living Spec: owed-item capability, owner predicates, use cases, UX notes and steering
  - **_Boundary**: docs/capabilities/, docs/usecases/, docs/ux/, docs/steering/
  - _Requirements: AC-01, AC-09_
  - **Verification**: `just docs-check`, `uv run devkit rules check`
