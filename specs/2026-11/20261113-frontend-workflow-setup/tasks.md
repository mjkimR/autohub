---
id: TASKS-frontend-workflow-setup
spec: SPEC-frontend-workflow-setup
plan: PLAN-frontend-workflow-setup
summary: "Repair configured setup and frontend fixing commands with regression coverage."
---

# [TASKS-frontend-workflow-setup] Frontend workflow repair

- [x] **Task 1**: Initialize frontend dependencies during configured worktree setup and retain failure propagation.
  - **_Boundary**: `.devkit/config.toml`, `modules/hub/tests/unit/scripts/test_frontend_workflow.py`, `docs/development/README.md`, `docs/development/toolchain.md`, `specs/2026-11/20261113-pending-decision-count/feedback/worktree-setup-skips-frontend-install.md`
  - _Requirements: AC-01, AC-04_
  - **Verification**: configured-command fixture checks and real `just init`; locked sync remains clean.

- [x] **Task 2**: Apply UI formatting and ESLint fixes in fixing mode while preserving read-only checks and selection.
  - **_Boundary**: `scripts/lint.sh`, `modules/hub/tests/unit/scripts/test_frontend_workflow.py`, `docs/development/README.md`, `docs/development/testing.md`, `specs/2026-11/20261113-pending-decision-count/feedback/lint-fix-skips-hub-ui-prettier.md`
  - _Requirements: AC-02, AC-03, AC-04_
  - **Verification**: focused command regressions, `just lint`, `just check` and document rules.
