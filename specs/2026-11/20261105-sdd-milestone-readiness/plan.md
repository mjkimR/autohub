---
id: PLAN-sdd-milestone-readiness
spec: SPEC-sdd-milestone-readiness
---

# Technical Plan: `SPEC-sdd-milestone-readiness` Preview executable SDD milestone work

## 1. Constitution & Invariant Review

No invariant changes. Preserve `ADR-milestone-readiness-boundary`, `CAP-SDD-native-delivery` admission and `CAP-SDD-runtime-isolation`. No database migration or dependency changes.

## 2. Architecture Overview & Impact
- Target Area: capabilities/sdd/
- Target Docs Blueprint: `PROP-sdd-milestone-readiness-target` (Living Spec targets for this plan and reconcile.md)

## 3. Component & Interface Design

Router → SddUseCase → preview service → GitHub reader and isolated runtime. Resolve ref once; restore runtime once at that SHA. Use devkit catalog/resolver for global/package/archive anchors. Extract shared read-only admission without changing start effects. Evaluate sequentially within 150 seconds.

`POST /api/v1/projects/{project_id}/sdd/milestone-preview` accepts `ref`, `milestone_id`, optional exact `milestone_path`. Return identity/SHA, milestone, observation/runtime basis, complete flag/reasons, counts/limits, graph and member admission/scheduling/workflow-hold facets. Validate access and enabled SDD project first.

No persisted state. UI selection starts empty, includes eligible direct members only and orders canonical IDs deterministically. Context changes/refresh cancel and invalidate stale requests. Exact graph semantics and limits are retained in `SPEC-sdd-milestone-readiness`. Missing/ambiguous milestones refuse; member/runtime failures disclose incomplete observations.

### Planned Boundaries:
- `modules/hub-ui/src/lib/api/`
- `modules/hub/app/features/project_management/sdd/`
- `modules/hub/app/features/project_management/repositories/`
- `modules/hub/tests/integration/features/project_management/sdd/`
- `modules/hub/tests/unit/features/project_management/sdd/`
- `modules/hub-ui/src/lib/features/project-management/repositories/`
- `docs/capabilities/repository/`
- `docs/capabilities/sdd/`
- `docs/usecases/repository/`
- `docs/usecases/sdd/`
- `docs/ux/repository/`
- `docs/ux/sdd/`
- `docs/steering/`

### Excluded Boundaries:
- `docs/operations/`
- `.github/`
- `packages/sdk/`

## 6. Verification & Test Plan

AC-01–AC-08: backend tests cover zero mutation, pinned reads, admission parity, workflow holds, exact dependencies, ownership, 50/51 members, 200/201 anchors, 500/501 edges, deadlines and partial failures. UI tests cover eligible-only subset order and stale requests. Retain start and Roadmap regressions. Run `just gen-ui-api`, `just check-ui-api`, `just lint-check`, `just check`, focused backend/UI suites and the required real isolated SDD contracts. No locking semantics change is planned. Compare the absent endpoint/panel baseline with the tested after behavior; claim no numerical speedup.

Matching activity PRs use at most 10 pages of 100 results. A full tenth page or failed later page is incomplete evidence. Owned PR identity/revisions remain inspectable before enrollment; optional run evidence stays project-scoped. This additional read bound preserves the 150-second request deadline.

Exact source anchors open GitHub blob links at the captured SHA while retaining the panel. This routine link choice preserves the immutable basis even if the repository viewer still displays a mutable branch. It does not alter the reviewed panel arrangement or introduce an execution action.
