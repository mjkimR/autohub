---
id: TASKS-ci-static-references
spec: SPEC-ci-static-references
plan: PLAN-ci-static-references
---

# CI static reference tasks

- [x] **Task 1**: Add the read-only static reference checker and command regressions.
  - **_Boundary**: `scripts/check-ci-references.py`, `modules/hub/tests/unit/scripts/test_ci_references.py`
  - _Requirements: AC-01, AC-02, AC-03_
  - **Verification**: focused command tests reproduce Red then pass Green, and actual repository check passes.
- [x] **Task 2**: Wire the checker into backend lint and reflect its supported boundary.
  - **_Boundary**: `justfile`, `scripts/check-backend.sh`, `modules/hub/tests/unit/scripts/test_ci_references.py`, `docs/development/README.md`, `docs/development/testing.md`, `specs/2026-11/20261113-repo-locked-sdd-runtime/feedback/ci-workflow-manifest-paths-unchecked.md`
  - _Requirements: AC-04_
  - **Verification**: lint-hook failure/read-only regression and full lint/check pass; named source feedback is resolved only after verification.
