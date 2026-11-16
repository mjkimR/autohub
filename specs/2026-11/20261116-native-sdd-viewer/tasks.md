---
id: TASKS-native-sdd-viewer
spec: SPEC-native-sdd-viewer
plan: PLAN-native-sdd-viewer
---

# Task Breakdown: `SPEC-native-sdd-viewer`

- [x] **Task 1**: Implement typed repository document discovery, metadata, links and roadmap with tests.
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/repositories/documents/`, `modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts`
  - _Requirements: AC-02, AC-03, AC-04, AC-06_
  - **Verification**: Targeted document unit tests.
- [x] **Task 2**: Implement native document presentation and integrate the host with regression tests.
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/repositories/`, `modules/hub-ui/src/routes/layout.css`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06_
  - **Verification**: Native viewer and existing repository integration tests, all UI tests and build.
- [x] **Task 3**: Remove viewer distribution coupling and retain Python pin checks.
  - **_Boundary**: `modules/hub-ui/package.json`, `modules/hub-ui/package-lock.json`, `modules/hub-ui/vendor/`, `scripts/check-devkit.py`, `modules/hub/tests/unit/scripts/test_check_devkit.py`, `justfile`
  - _Requirements: AC-01, AC-07_
  - **Verification**: Pin checker unit tests, just check-devkit, just lint and just check.

Expected Living Spec outputs (sync output): `docs/capabilities/repository/CAP-DOC-repository-viewer.md`, `docs/usecases/repository/UC-inspect-repository-documents.md`, `docs/ux/repository/UX-repository.md`, `docs/architecture/ARCH-02-constraints.md`, `docs/architecture/ARCH-05-1-containers.md`, `docs/architecture/ARCH-05-2-components.md`, `docs/development/toolchain.md`, `docs/decisions/2026-11/20261116-native-sdd-viewer.md`, `docs/decisions/2026-11/20261105-sdd-development.md`.
