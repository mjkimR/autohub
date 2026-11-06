---
id: TASKS-work-plan-templates
spec: SPEC-work-plan-templates
plan: PLAN-work-plan-templates
---

# Tasks: `SPEC-work-plan-templates`

- [x] **Task 1**: Persist and expose strict revisioned definitions and actor-bound CRUD recovery.
  - **_Boundary**: `modules/hub/app/features/project_management/work_plans/`, `modules/hub/migrations/versions/`, `modules/hub/tests/integration/features/project_management/work_plans/`, `modules/hub/tests/integration/migrations/`
  - _Requirements: AC-01, AC-03, AC-05, AC-06_
  - **Verification**: focused API and migration tests, PostgreSQL race tests.
- [x] **Task 2**: Atomically register fresh reviewed Plans with immutable provenance through the ordinary owner.
  - **_Boundary**: `modules/hub/app/features/project_management/work_plans/`, `modules/hub/tests/integration/features/project_management/work_plans/`
  - _Requirements: AC-02, AC-03, AC-04, AC-05_
  - **Verification**: identity/atomicity/replay/owner compatibility and PostgreSQL barriers.
- [x] **Task 3**: Deliver template management, fresh preview/review and durable original-intent recovery; reflect owning contracts.
  - **_Boundary**: `modules/hub-ui/src/lib/api/generated/work-plan.d.ts`, `modules/hub-ui/src/lib/stores/session.svelte.ts`, `modules/hub-ui/src/lib/stores/session.test.ts`, `modules/hub-ui/src/lib/features/project-management/work-plans/`, `docs/capabilities/work-plans/`, `docs/usecases/work-plans/`, `docs/ux/work-plans/`, `docs/steering/glossary.md`, `docs/steering/ux-objects.md`
  - _Requirements: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06_
  - **Verification**: UI tests, API generation, just lint/check, independent reviews.
