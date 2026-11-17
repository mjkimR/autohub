---
id: TASKS-sdd-gate-question
spec: SPEC-sdd-gate-question
plan: PLAN-sdd-gate-question
---

# Task Breakdown: `SPEC-sdd-gate-question` Surface repository workflow gates through the question channel

## Phase 1: Implementation

- [ ] **Task 1.1**: Add the gate paragraph to SDD activity instructions
  - **_Boundary**: `modules/hub/app/features/project_management/pipeline_runs/requests.py`
  - _Requirements: AC-01, AC-02, AC-03_
  - **Verification**: `test_requests.py` SDD and non-SDD instruction tests pass
- [ ] **Task 1.2**: Prove the mention comment carries the gate instruction
  - **_Boundary**: `modules/hub/tests/unit/features/project_management/pipeline_runs/test_requests.py`, `modules/hub/tests/unit/features/project_management/pipeline_runs/test_dispatch.py`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: the new unit tests pass and fail against the previous instruction text
- [ ] **Task 1.3**: Keep the gate question decision flow as a regression check
  - **_Boundary**: `modules/hub/tests/integration/features/project_management/pipeline_runs/test_optimistic_sdd.py` (run only; edit only if an assertion contradicts the new text)
  - _Requirements: AC-05_
  - **Verification**: `test_agent_question_after_push_pauses_before_ci_and_uses_current_head` and `test_enrollment_has_only_descriptive_intent_and_no_repository_readiness` pass

## Phase 2: Checks

- [ ] **Task 2.1**: Run repository checks
  - **_Boundary**: none (commands only)
  - _Requirements: AC-01, AC-05_
  - **Verification**: `just lint` and `just check` pass
