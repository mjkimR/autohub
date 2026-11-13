---
id: TASKS-owed-counts-error-reason
spec: SPEC-owed-counts-error-reason
plan: PLAN-owed-counts-error-reason
---

# Counts failure reason tasks

- [x] **Task 1**: Restore shared failure reason state and Projects tooltip with recovery and session regression tests.
  - **_Boundary**: `modules/hub-ui/src/lib/features/attention/owed-counts.svelte.ts`, `modules/hub-ui/src/lib/features/attention/owed-counts.test.ts`, `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte`, `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.integration.test.ts`, `modules/hub-ui/src/lib/components/shared/AppShell.integration.test.ts`, `docs/ux/projects/UX-projects.md`
  - _Requirements: AC-01, AC-02, AC-03, AC-04_
  - **Verification**: focused Vitest store, Projects and shell integration tests; full `just lint` and `just check`.
