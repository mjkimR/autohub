---
id: TASKS-repo-path-runtime-sources
spec: SPEC-repo-path-runtime-sources
plan: PLAN-repo-path-runtime-sources
---

# Task Breakdown: `SPEC-repo-path-runtime-sources` Install repository-local path sources in the SDD runtime

## Phase 1: Decision

- [x] **Task 1.1**: Record the path source decision as an ADR that supersedes the identity clause in part
  - **_Boundary**: `docs/decisions/2026-11/20261113-repository-path-sources.md`, `docs/decisions/2026-11/20261113-repository-locked-runtime.md` `(scope extension: decision-writing requires the partial-supersession pointer in ADR-repository-locked-runtime for its runtime identity clause)`
  - _Requirements: AC-02, AC-03_
  - **Verification**: `uv run devkit rules check docs/decisions/2026-11`

## Phase 2: Implementation

- [x] **Task 2.1**: Select in-checkout path sources, capture their trees and add their digests to the identity, with unit tests and fixtures
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/lock_runtime.py`, `modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py`, `modules/hub/tests/unit/features/project_management/sdd/fixtures/`, `modules/hub/app/features/project_management/sdd/diagnostics.py` `(scope extension: the SDD_RUNTIME_SOURCE_UNSUPPORTED and SDD_RUNTIME_INSTALL_FAILED catalog text of CAP-SDD-runtime-isolation rule 25 must name in-repository path sources)`, `modules/hub/app/features/project_management/sdd/runtime.py`, `docs/steering/glossary.md` `(scope extension: the Runtime identity entry restates CAP-SDD-runtime-isolation rule 2, which now covers path source content)`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: `just test tests/unit/features/project_management/sdd/test_lock_runtime.py`
- [x] **Task 2.2**: Stage captured path sources in the Hub process and build them in the sandbox, with unit and integration tests
  - **_Boundary**: `modules/hub/app/features/project_management/sdd/runtime_install.py`, `modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py`, `modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py`
  - _Requirements: AC-05, AC-06_
  - **Verification**: `just test tests/unit/features/project_management/sdd/test_runtime_install.py` and `just test-sdd <seed>`
