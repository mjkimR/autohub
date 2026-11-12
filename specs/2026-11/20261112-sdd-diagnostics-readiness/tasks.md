---
id: TASKS-sdd-diagnostics-readiness
spec: SPEC-sdd-diagnostics-readiness
plan: PLAN-sdd-diagnostics-readiness
---

# Task Breakdown: `SPEC-sdd-diagnostics-readiness`

## Implementation

- [ ] **Task 1**: Project bounded structured diagnostics and preserve them through evaluation failures, with regression tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/`, `modules/hub/tests/unit/features/project_management/sdd/`, `modules/hub/tests/integration/features/project_management/sdd/`
  - _Requirements: AC-01, AC-02, AC-03_
  - **Verification**: Owning backend diagnostic, runtime, service, readiness and progress tests prove safe projection and stable identity.
- [ ] **Task 2**: Render shared diagnostics and selected-combination readiness context, with integration tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/repositories/`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/`, `modules/hub-ui/src/lib/api/` (sync output)
  - _Requirements: AC-04, AC-05, AC-06_
  - **Verification**: Focused Vitest registration/native review tests; `just check-ui-api`, `just lint`, `just check`.
- [ ] **Task 3**: Align current diagnostic, registration and execution contracts with the retained implementation
  - **_Boundary**: `docs/capabilities/sdd/CAP-SDD-runtime-isolation.md`, `docs/capabilities/sdd/CAP-SDD-workflow-control.md`, `docs/usecases/sdd/UC-complete-sdd-workflow.md`, `docs/ux/sdd/UX-sdd-execution.md`, `docs/ux/sdd/UX-sdd-run.md`, `docs/steering/ux-objects.md`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06_
  - **Verification**: Current contracts match source/test inspection; `just docs-check` and `git diff --check`.
