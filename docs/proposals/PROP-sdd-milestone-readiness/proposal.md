---
id: PROP-sdd-milestone-readiness
title: Preview executable SDD milestone work
summary: "Expose selected milestone members and authoritative readiness so operators can review a sequential execution selection without starting work."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/sdd/
priority: high
size: M
planning_effort: medium
dev_effort: high
milestone: MS-native-sdd-execution
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/app/features/project_management/repositories/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub/tests/unit/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/repositories/
    - docs/capabilities/repository/
    - docs/capabilities/sdd/
    - docs/usecases/repository/
    - docs/usecases/sdd/
    - docs/ux/repository/
    - docs/ux/sdd/
    - docs/steering/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-sdd-milestone-readiness] Preview executable SDD milestone work

## 1. Background & Hypothesis

`CAP-DOC-repository-viewer` displays branch-specific milestone members, and `CAP-SDD-native-delivery` exposes individual native activity admission. There is no Hub-owned preview that resolves a milestone selection into inspectable executable activities. A read-only readiness contract can establish the selection basis before sequential execution is added.

### Source anchors

`modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts` covers selected-branch member navigation. `modules/hub/app/features/project_management/sdd/activities.py` owns individual start admission. Neither read-only milestone navigation nor a displayed document is execution authority.

## 2. Technical Spike Findings

The inspected source and design comparison are retained in `MAT-sdd-milestone-readiness`.

- **Q1 resolved**: Resolve the requested branch once to a full commit SHA. Discover global and registered package roadmap roots, including `_archive`, with devkit's document catalog at that SHA. Membership consists only of direct proposal anchors whose `milestone` resolves to the requested milestone ID. Historical spec milestone metadata never adds members.
- **Q2 resolved**: Reuse `start_blocker`, `planning_blocker`, existing project validation and branch ownership checks through a shared read-only evaluator. Restore the server-selected runtime once per preview and call devkit policy/workflow commands inside its isolated checkout. Do not use the Proposals screen's `actions` hint as eligibility authority. Existing activities are inspect-only rows; this preview creates and resumes nothing.
- **Q3 resolved**: Bound discovery and evaluation explicitly. The first implementation supports at most 50 direct members, 200 distinct prerequisite anchors and 500 dependency edges, a 150-second request deadline, and at most four concurrent unit evaluations within one pinned checkout. These are conservative limits to test, not measured performance claims. Return observed counts, configured limits and all incomplete reasons. A partial preview permits inspection but disables selection and ordered-selection output.

## 3. Proposed Design & Impact

### Planning decisions

`PADR-milestone-readiness-boundary` records the boundary between repository inspection and native readiness.

1. Add a Hub-owned milestone preview panel beside the existing native SDD surfaces. It accepts the current repository branch and an explicit milestone chosen from a Hub-owned selector. Viewer selection may prefill a recognized milestone path through the existing callback; correctness never depends on undocumented vendor events. No vendor changes are required.
2. Add a read-only `POST /api/v1/projects/{project_id}/sdd/milestone-preview` request with `ref`, `milestone_id` and optional exact `milestone_path`. Resolve the project repository/connector server-side. Read all document content at `resolved_sha`; reject ambiguous or missing IDs, path traversal and a path/ID mismatch. Never fall back to main. Support archived and package milestones for inspection; a done/dropped milestone cannot produce an executable selection.
3. Return project/repository identity, requested ref, resolved SHA, milestone ID/path/status, observation time, runtime identity, complete flag, observed counts/limits, warnings, prerequisite graph and member rows. Each member identifies its exact proposal anchor, activity kind, workflow stage, eligibility, hold reasons and related project-scoped run/PR evidence. Runtime errors and unknown evidence produce `unknown`, never ready. A missing requested milestone is a request refusal; an unreadable member/dependency is an incomplete preview with its exact path/ID.
4. Separate `eligible_now`, `held`, `existing_activity`, `finished`, `unsupported` and `unknown`. A draft may offer Planning after existing admission checks; an accepted proposal may offer handoff-first Development. Reviewing/rejected proposals do not offer a new activity. Existing owned activity PRs/runs link to inspection; an unrelated branch reports `SDD_BRANCH_EXISTS`. Existing spec readiness remains in `UX-sdd-execution`: the preview never invents a PR number or independently enrolls a spec.
5. Read `depends_on` exactly. Milestone prerequisites resolve only MS IDs; work prerequisites resolve PROP/SPEC IDs using devkit's catalog/resolver, including historical anchors and aliases. Duplicate IDs, cycles, dangling edges and malformed relations prevent a complete selectable result. Display dependency source, canonical ID, anchor path and status. Do not infer dependencies from text, slugs, milestone order or shared boundaries.
6. A milestone dependency is satisfied only when its resolved status is done; dropped is visible as a hold because abandonment does not establish delivery. A SPEC prerequisite is satisfied only when completed at the captured SHA. A PROP prerequisite stays held while draft, reviewing, accepted or rejected. A handed-off PROP reference can be satisfied only when devkit resolves it unambiguously to a completed SPEC; recorded `handoff_from` may supply an inspection link but never repairs an unresolved source reference or proves completion. These conservative readiness semantics are a Hub preview projection; devkit still owns workflow admission. No proposal acceptance, milestone completion or live-run state substitutes for a completed prerequisite.
7. Selection is ephemeral UI state, initially empty, restricted to eligible direct member activities. Choosing a subset never silently includes held members or external prerequisites. For a complete graph, show a deterministic topological order with canonical ID tie-breaking. Unfinished prerequisite members remain held even if selected elsewhere: the order is a review recommendation, not a prediction that earlier work will complete or release later work. Do not reorder/edit the repository or persist a queue.
8. Project/ref/milestone changes and explicit refresh clear selection and invalidate prior results. Cancel obsolete requests and ignore late responses. Display the captured SHA throughout. Repository data is a commit snapshot; run/PR evidence is a separately timestamped observation with exact head/base IDs where available. Do not label external evidence as atomic with the snapshot. Any future execution must re-evaluate admission; there is no execution control or authority token in this response.

### Acceptance criteria for Development

- **MR-01**: Given an eligible milestone, when previewed and a subset selected, then repository refs/content, activities, PRs, runs, decisions and scheduler state remain unchanged. Assert zero calls to all execution/publication/enrollment collaborators.
- **MR-02**: Given global/package and active/archive milestones on two different branches, when each is previewed, then membership and every document/dependency read use its resolved SHA. A branch moving during reads cannot mix contents. Historical SPEC milestone fields add no members.
- **MR-03**: Given an eligible draft, accepted proposal, reviewing/rejected proposal, inactive lifecycle, malformed worker envelope or unavailable runtime, when previewed, then the row shows the existing admission result or a held/unknown outcome with exact reason. The preview and start path share the evaluator and parity fixtures.
- **MR-04**: Given missing, ambiguous, cyclic, incomplete, dropped or unfinished prerequisites, when previewed, then the graph exposes exact anchors/reasons and no affected member is selectable. Completed SPEC prerequisites pass; accepted PROP prerequisites do not. Test explicit handed-off resolution separately from a missing PROP with a same-slug spec.
- **MR-05**: Given an existing owned activity or unrelated branch, when previewed, then show inspect-only project-scoped run/PR evidence or branch conflict respectively. Same slugs in another project and absent lineage never create links or readiness.
- **MR-06**: Given 50/51 members, 200/201 anchors, 500/501 edges, truncated repository enumeration, deadline, pagination failure or partial runtime failure, then exact boundaries are tested and the response discloses incompleteness. Incomplete previews expose no selectable order. Do not silently slice the existing 50-item Proposals list and call it complete.
- **MR-07**: Given an empty selection and complete preview, when an operator selects eligible members, then only those exact activities appear in deterministic order. Ref/project/milestone change or refresh clears it; a delayed prior response cannot restore it. Empty results offer another milestone or refresh.
- **MR-08**: Given a non-SDD or unauthorized project, invalid path or ambiguous milestone, when preview is requested, then existing access/project validation refuses before evaluation or artifact creation. Existing single-activity start and viewer branch navigation retain their regression coverage.

### Implementation and verification outline

Keep Router → UseCase → Service → Repository ownership. Add bounded preview schemas/API and an orchestration service in the existing SDD feature. Reuse repository reads, devkit catalog/resolution and isolated runtime; extract only the read-only start evaluation needed for parity, without altering start effects. Keep UI state in a separate component under the repository feature to respect component size limits. Regenerate the typed API client.

Development adds focused unit/integration fixtures for the criteria above and a UI integration suite for subset selection, incomplete states and stale responses. Run backend initialization, `just gen-ui-api`, focused tests, `just lint` and `just check`. Planning checks documents and evidence only; no product tests or deployment checks are claimed here. No numerical before/after performance claim is proposed.

### Non-goals

- **Scope Excluded**: Starting batches or individual activities from this preview, durable selection/queues, resumptions, automatic approvals, inferred dependencies, modifying the vendored viewer and Work Plan binding.
- **Scope Excluded**: New devkit commands or workflow policy, downstream spec discovery by guessed lineage, pilot operation, deployment, production verification, monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

Planning recommends the separate preview panel and pinned read-only evaluation. `dev_effort: high` is retained for runtime, dependency and multi-surface verification. No unresolved business choice requires a question round. The Host presents both UX candidates and the committed source for plan-accept; this turn records no acceptance or handoff.

Acceptance and Development handoff follow `sdd-proposal`. Completion requires a verified accepted implementation, not this Planning result.
