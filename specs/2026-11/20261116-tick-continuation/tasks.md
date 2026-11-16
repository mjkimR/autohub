---
id: TASKS-tick-continuation
spec: SPEC-tick-continuation
plan: PLAN-tick-continuation
---

# Task Breakdown: `SPEC-tick-continuation`

- [x] **Task 1**: Bound SDK maintenance continuation with recovery and wait regressions.
  - **_Boundary**: `modules/hub/app/features/execution/flows/worker.py`, `modules/hub/tests/integration/features/execution/flows/`
  - _Requirements: AC-01, AC-02_
  - **Verification**: flow host and recovery integration suites.
- [x] **Task 2**: Advance committed SDD starts and PR resumes with shared capacity checks.
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/usecases.py`, `modules/hub/app/features/project_management/pipeline_runs/usecases/`, `modules/hub/tests/unit/features/project_management/pipeline_runs/usecases/`, `modules/hub/tests/integration/features/project_management/sdd/`, `modules/hub/tests/integration/features/project_management/pipeline_runs/`
  - _Requirements: AC-03_
  - **Verification**: prompt and queue-capacity tests plus affected API suites.
- [x] **Task 3**: Stabilize system-owned interval cadence with dispatcher regressions.
  - **_Boundary**: `modules/hub/app/features/execution/dispatchers/services.py`, `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services.py`
  - _Requirements: AC-04_
  - **Verification**: dispatcher unit and integration suites.

Expected sync outputs: `CAP-SDK-task-flow-execution`, `CAP-SDD-native-delivery`, `CAP-PR-pull-request-delivery`, `CAP-EXEC-scheduling-maintenance`, `UC-execute-task-flow`, `UC-start-sdd-activity`, `UC-complete-sdd-workflow`, `UC-run-due-work`.
