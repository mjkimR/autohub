---
id: SPEC-sdd-milestone-readiness
title: Preview executable SDD milestone work
summary: Expose selected milestone members and authoritative readiness so operators can review a sequential execution selection without starting work.
status: in-progress
created: 2026-11-05
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-sdd-milestone-readiness] Preview executable SDD milestone work

## 1. Problem Statement & Motivation

Handed off from proposal PROP-sdd-milestone-readiness on 2026-11-05.
- **Preserved Materials**: `docs/materials/2026-11/20261105-sdd-milestone-readiness`
- Target Docs Blueprint: `PROP-sdd-milestone-readiness-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

`CAP-DOC-repository-viewer` displays branch-specific milestone members, and `CAP-SDD-native-delivery` exposes individual native activity admission. There is no Hub-owned preview that resolves a milestone selection into inspectable executable activities. A read-only readiness contract can establish the selection basis before sequential execution is added.

#### Source anchors

`modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts` covers selected-branch member navigation. `modules/hub/app/features/project_management/sdd/activities.py` owns individual start admission. Neither read-only milestone navigation nor a displayed document is execution authority.

## 2. User Stories

- **US-1**: As an operator, I want to inspect exact milestone members and select eligible activities locally to review work without starting execution.

## 3. Non-Goals

1. **Scope Excluded**: Activity starts, persisted queues, resumptions, approvals, guessed lineage, vendor changes, new devkit commands, deployments and Work Plan binding.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] MR-01: previewed and a subset selected
- **Given** an eligible milestone
- **When** previewed and a subset selected
- **Then** repository refs/content, activities, PRs, runs, decisions and scheduler state remain unchanged. Assert zero calls to all execution/publication/enrollment collaborators.

### [AC-02] MR-02: each is previewed
- **Given** global/package and active/archive milestones on two different branches
- **When** each is previewed
- **Then** membership and every document/dependency read use its resolved SHA. A branch moving during reads cannot mix contents. Historical SPEC milestone fields add no members.

### [AC-03] MR-03: previewed
- **Given** an eligible draft, accepted proposal, reviewing/rejected proposal, inactive lifecycle, malformed worker envelope or unavailable runtime
- **When** previewed
- **Then** the row shows the existing admission result or a held/unknown outcome with exact reason. The preview and start path share admission evaluation and parity fixtures. Separate preview hold fixtures cover intent-proposal done with blocked workers, pending questions and malformed workers, including accepted proposals; start behavior stays unchanged.

### [AC-04] MR-04: previewed
- **Given** missing, ambiguous, cyclic, incomplete or unfinished prerequisites
- **When** previewed
- **Then** the graph exposes exact anchors/reasons and no affected member is selectable. Done/dropped milestone prerequisites pass. Exact completed SPEC prerequisites pass without reopening their history; accepted PROP prerequisites do not. Test explicit handed-off resolution separately from a missing PROP with a same-slug spec.

### [AC-05] MR-05: previewed
- **Given** an existing owned activity or unrelated branch
- **When** previewed
- **Then** show inspect-only project-scoped run/PR evidence or branch conflict respectively. Same slugs in another project and absent lineage never create links or readiness.

### [AC-06] MR-06: the milestone preview is requested
- **Given** 50/51 members, 200/201 anchors, 500/501 edges, truncated repository enumeration, deadline, pagination failure or partial runtime failure
- **When** the milestone preview is requested
- **Then** exact boundaries are tested and the response discloses incompleteness. Incomplete previews expose no selectable order. Do not silently slice the existing 50-item Proposals list and call it complete.

### [AC-07] MR-07: an operator selects eligible members
- **Given** an empty selection and complete preview
- **When** an operator selects eligible members
- **Then** only those exact activities appear in deterministic order. Ref/project/milestone change or refresh clears it; a delayed prior response cannot restore it. Empty results offer another milestone or refresh.

### [AC-08] MR-08: preview is requested
- **Given** a non-SDD or unauthorized project, invalid path or ambiguous milestone
- **When** preview is requested
- **Then** existing access/project validation refuses before evaluation or artifact creation. Existing single-activity start and viewer branch navigation retain their regression coverage.

## 5. Approved Design and Constraints

The accepted direction below governs implementation with AC-01 through AC-08.

### 2. Technical Spike Findings

The inspected source and design comparison are retained in `MAT-sdd-milestone-readiness`.

- **Q1 resolved**: Resolve the requested branch once to a full commit SHA. Discover global and registered package roadmap roots, including `_archive`, with devkit's document catalog at that SHA. Membership consists only of direct proposal anchors whose `milestone` resolves to the requested milestone ID. Historical spec milestone metadata never adds members.
- **Q2 resolved**: Reuse `start_blocker`, `planning_blocker`, existing project validation and branch ownership checks through a shared read-only evaluator. Restore the server-selected runtime once per preview and call devkit policy/workflow commands inside its isolated checkout. Do not use the Proposals screen's `actions` hint as eligibility authority. Existing activities are inspect-only rows; this preview creates and resumes nothing.
- **Q3 resolved**: Bound discovery and evaluation explicitly. The first implementation supports at most 50 direct members, 200 distinct prerequisite anchors and 500 dependency edges, a 150-second request deadline, and sequential per-unit evaluation within one pinned checkout. These are conservative limits to test, not measured performance claims. Return observed counts, configured limits and all incomplete reasons. A partial preview permits inspection but disables selection and ordered-selection output.

### 3. Proposed Design & Impact

#### Planning decisions

`ADR-milestone-readiness-boundary` records the boundary between repository inspection and native readiness.

1. Add a Hub-owned milestone preview panel beside the existing native SDD surfaces. It accepts the current repository branch and an explicit milestone chosen from a Hub-owned selector. Viewer selection may prefill a recognized milestone path through the existing callback; correctness never depends on undocumented vendor events. No vendor changes are required.
2. Add a read-only `POST /api/v1/projects/{project_id}/sdd/milestone-preview` request with `ref`, `milestone_id` and optional exact `milestone_path`. Resolve the project repository/connector server-side. Read all document content at `resolved_sha`; reject ambiguous or missing IDs, path traversal and a path/ID mismatch. Never fall back to main. Support archived and package milestones for inspection; a done/dropped milestone cannot produce an executable selection.
3. Return project/repository identity, requested ref, resolved SHA, milestone ID/path/status, observation time, runtime identity, complete flag, observed counts/limits, warnings, prerequisite graph and member rows. Each member identifies its exact proposal anchor, activity kind, workflow stage, separate activity-admission and preview-scheduling results, eligibility, hold reasons and related project-scoped run/PR evidence. Runtime errors and unknown evidence produce `unknown`, never ready. Reuse `read_hold` and `held` for blocked workers, pending questions and malformed worker evidence. Evaluate workflow holds for both draft and accepted proposals; selection requires admission, dependency scheduling and workflow-hold facets all to pass. Preserve existing single-start behavior: the preview scheduling result adds no start gate or refusal. A missing requested milestone is a request refusal; an unreadable member/dependency is an incomplete preview with its exact path/ID.
4. Separate `eligible_now`, `held`, `existing_activity`, `finished`, `unsupported` and `unknown`. A draft may offer Planning after existing admission checks; an accepted proposal may offer handoff-first Development. Reviewing/rejected proposals do not offer a new activity. Existing owned activity PRs/runs link to inspection; an unrelated branch reports `SDD_BRANCH_EXISTS`. Existing spec readiness remains in `UX-sdd-execution`: the preview never invents a PR number or independently enrolls a spec.
5. Read `depends_on` exactly. Milestone prerequisites resolve only MS IDs; work prerequisites resolve PROP/SPEC IDs using devkit's catalog/resolver, including historical anchors and aliases. Duplicate IDs, cycles, dangling edges and malformed relations prevent a complete selectable result. Display dependency source, canonical ID, anchor path and status. Do not infer dependencies from text, slugs, milestone order or shared boundaries.
6. Follow devkit spec-next next-work scheduling semantics: a milestone dependency is satisfied when done or dropped. A direct unit prerequisite is satisfied only by an exact ID resolving to one completed SPEC at the captured SHA. Do not traverse or reopen a completed SPEC's own prerequisites. A PROP prerequisite stays held while draft, reviewing, accepted or rejected. A handed-off PROP reference in an active proposal is repair-needed unless an explicit canonical mapping resolves it unambiguously to that completed SPEC; historical-reference tolerance and matching slugs do not supply such a mapping. Recorded `handoff_from` supplies inspection links only. These are scheduling observations, separate from native workflow admission; this feature changes no start gate.
7. Selection is ephemeral UI state, initially empty, restricted to eligible direct member activities. Choosing a subset never silently includes held members or external prerequisites. For a complete graph, show a deterministic topological order with canonical ID tie-breaking. Unfinished prerequisite members remain held even if selected elsewhere: the order is a review recommendation, not a prediction that earlier work will complete or release later work. Do not reorder/edit the repository or persist a queue.
8. Project/ref/milestone changes and explicit refresh clear selection and invalidate prior results. Cancel obsolete requests and ignore late responses. Display the captured SHA throughout. Repository data is a commit snapshot; run/PR evidence is a separately timestamped observation with exact head/base IDs where available. Do not label external evidence as atomic with the snapshot. Any future execution must re-evaluate admission; there is no execution control or authority token in this response.

#### Acceptance criteria for Development

- **MR-01**: Given an eligible milestone, when previewed and a subset selected, then repository refs/content, activities, PRs, runs, decisions and scheduler state remain unchanged. Assert zero calls to all execution/publication/enrollment collaborators.
- **MR-02**: Given global/package and active/archive milestones on two different branches, when each is previewed, then membership and every document/dependency read use its resolved SHA. A branch moving during reads cannot mix contents. Historical SPEC milestone fields add no members.
- **MR-03**: Given an eligible draft, accepted proposal, reviewing/rejected proposal, inactive lifecycle, malformed worker envelope or unavailable runtime, when previewed, then the row shows the existing admission result or a held/unknown outcome with exact reason. The preview and start path share admission evaluation and parity fixtures. Separate preview hold fixtures cover intent-proposal done with blocked workers, pending questions and malformed workers, including accepted proposals; start behavior stays unchanged.
- **MR-04**: Given missing, ambiguous, cyclic, incomplete or unfinished prerequisites, when previewed, then the graph exposes exact anchors/reasons and no affected member is selectable. Done/dropped milestone prerequisites pass. Exact completed SPEC prerequisites pass without reopening their history; accepted PROP prerequisites do not. Test explicit handed-off resolution separately from a missing PROP with a same-slug spec.
- **MR-05**: Given an existing owned activity or unrelated branch, when previewed, then show inspect-only project-scoped run/PR evidence or branch conflict respectively. Same slugs in another project and absent lineage never create links or readiness.
- **MR-06**: Given 50/51 members, 200/201 anchors, 500/501 edges, truncated repository enumeration, deadline, pagination failure or partial runtime failure, then exact boundaries are tested and the response discloses incompleteness. Incomplete previews expose no selectable order. Do not silently slice the existing 50-item Proposals list and call it complete.
- **MR-07**: Given an empty selection and complete preview, when an operator selects eligible members, then only those exact activities appear in deterministic order. Ref/project/milestone change or refresh clears it; a delayed prior response cannot restore it. Empty results offer another milestone or refresh.
- **MR-08**: Given a non-SDD or unauthorized project, invalid path or ambiguous milestone, when preview is requested, then existing access/project validation refuses before evaluation or artifact creation. Existing single-activity start and viewer branch navigation retain their regression coverage.

#### Implementation and verification outline

Keep Router → UseCase → Service → Repository ownership. Add bounded preview schemas/API and an orchestration service in the existing SDD feature. Reuse repository reads, devkit catalog/resolution and isolated runtime; extract only the read-only start evaluation needed for parity, without altering start effects. Keep UI state in a separate component under the repository feature to respect component size limits. Regenerate the typed API client.

Development adds focused unit/integration fixtures for the criteria above and a UI integration suite for subset selection, incomplete states and stale responses. Run backend initialization, `just gen-ui-api`, focused tests, `just lint` and `just check`. Planning checks documents and evidence only; no product tests or deployment checks are claimed here. No numerical before/after performance claim is proposed.

#### Non-goals

- **Scope Excluded**: Starting batches or individual activities from this preview, durable selection/queues, resumptions, automatic approvals, inferred dependencies, modifying the vendored viewer and Work Plan binding.
- **Scope Excluded**: New devkit commands or workflow policy, downstream spec discovery by guessed lineage, pilot operation, deployment, production verification, monitoring, incident detection and CI trigger changes.

### 4. Lifecycle & Retirement Criteria

Planning recommends the separate preview panel and pinned read-only evaluation. `dev_effort: high` is retained for runtime, dependency and multi-surface verification. The challenger's two findings were folded into shared scheduling semantics and separate admission/workflow-hold facets. The requested UX review's two findings were folded into object ownership and transition coverage; its original open findings remain visible for plan-accept. No unresolved business choice requires a question round. The Host presents both UX candidates and the committed source for plan-accept; this turn records no acceptance or handoff.

Acceptance and Development handoff follow `sdd-proposal`. Completion requires a verified accepted implementation, not this Planning result.


## 6. Screens


#### Candidates and recommendation

- **A — separate Hub panel (recommended)**: Keep the milestone selector, captured basis and readiness table together beside repository/native execution content. Row detail holds exact prerequisite evidence. A selection summary follows the table. This keeps the review goal in one place and does not depend on vendor selection state.
- **B — dedicated Hub preview screen**: Navigate from the repository surface to a screen with a full-width member table and a separate review step for the selection. This gives more room for large graphs, but adds navigation/state restoration for a bounded 50-member preview. Defer this alternative unless the bounded panel proves insufficient.

The recommendation is a routine design assumption within the authorized read-only scope. Optional independent UX review was requested and is recorded in this bundle's envelopes.

#### UX-sdd-milestone-preview — panel draft

**Purpose**: Review an exact milestone's currently eligible activities and an explicit local subset. The facts needed are repository/ref/SHA, milestone identity, completeness and prerequisite reasons. Runtime diagnostics and related executions are secondary disclosures.

**Content**: The member table is primary. The captured basis and completeness notice sit above it; local selection and suggested order follow it. Row details reveal exact dependency anchors and activity links. Style follows `modules/hub-ui/src/routes/layout.css` and existing repository controls.

- Repository viewer: project/repository, ref, captured SHA and refresh control.
- Repository viewer: milestone selector and Preview milestone action.
- SDD unit: member rows with exact proposal IDs/paths.
- SDD unit: eligibility, proposed Planning or handoff-first Development, exact prerequisite reasons, selection checkbox when eligible.
- Native SDD activity: timestamped workflow/runtime evidence and existing activity links, when available.
- PR run: existing project-scoped execution/PR link, when recorded.
- SDD unit: selected activities and suggested order, only for a complete preview.

**States**:

- `empty`: No milestone selected or no members found; choose a milestone or refresh. A complete zero-member result says no direct proposal members rather than completed delivery.
- `loading`: Announce preview progress, disable selection, retain the requested ref/milestone visibly and permit cancellation by changing context.
- `populated`: Show all bounded rows, exact basis and unchecked eligible choices. Inspect rows, select a subset or refresh.
- `held`: Show nonselectable held rows with dependency or admission reasons; inspect source or choose other eligible rows.
- `incomplete`: Announce exact missing coverage/limits above the table; disable selection/order and offer refresh or another milestone.
- `selected`: Show selected IDs/activity kinds and deterministic order with an observation-only notice; allow deselection, clear or end inspection.
- `stale`: On context change/refresh discard result and selection, then request the current context. Ignore a late obsolete response.
- `error`: Show access/ref/runtime/request error with applicable retry or corrected selection; no readiness is retained.

**Interactions**:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose ref/milestone | UC-preview-sdd-milestone 1 | empty, loading, populated, selected, held, incomplete, error | stale | | `CAP-SDD-native-delivery` | Prior selection clears and the chosen basis appears. |
| Preview or refresh | UC-preview-sdd-milestone 2 | empty, populated, selected, held, incomplete, error | loading | | `CAP-SDD-native-delivery` | Prior selection clears; obsolete responses are invalidated. Matching basis, completeness and member rows appear, or the exact refusal appears. |
| Expand member prerequisites | UC-preview-sdd-milestone 3 | populated, held, incomplete | same | | `CAP-SDD-native-delivery` | Exact prerequisite IDs, anchors, status and hold reasons appear. |
| Open source anchor | UC-preview-sdd-milestone 3 | populated, held, incomplete | same | `UX-repository` | `CAP-DOC-repository-viewer` | Read the anchor at the captured SHA. |
| Open existing execution | UC-preview-sdd-milestone 3 | populated, held | same | `UX-run-decisions` | `CAP-SDD-native-delivery` | Open recorded run without resuming or approving it. |
| Select/deselect eligible member | UC-preview-sdd-milestone 4 | populated, selected | selected | | `CAP-SDD-native-delivery` | Exact subset/order changes; no execution starts. |
| Clear selection | UC-preview-sdd-milestone 4 | selected | populated | | `CAP-SDD-native-delivery` | Selected count returns to zero. |
| End inspection | UC-preview-sdd-milestone 5 | populated, selected, held, incomplete, error | end | back | `CAP-SDD-native-delivery` | Return to repository content without saving a queue. |

**Register changes**: Extend the SDD unit row with milestone member/prerequisite representation and select subset, inspect order and clear selection actions. Extend Repository viewer representations with milestone selector and captured preview basis, plus Preview milestone action. Do not add Work Plan/Work Item rows or rename existing terms. These are representations of existing objects, not a new execution domain object.


## 7. Assumptions and Baseline

The accepted head is `8f5003e54b8943ef80ca4c63ac92968482c3864e`. Its product source matches main `658042b3d9e3f0423416b6655b4c2d2a6353e166`; handoff documents differ. Existing proposal admission and branch-specific viewer navigation remain valid premises. Candidate A and the retained Planning UX review apply unchanged. The baseline has no milestone preview endpoint or eligible-subset panel. Verify the after behavior through API/UI fixtures; claim no performance improvement.

The pinned devkit resolver admits aliases only within the document prefix. Preview trusts only its returned canonical document. A recorded proposal origin or a same-slug completed SPEC supplies no mapping. Supported SPEC aliases are verified with the real isolated runtime; a cross-prefix mapping is tested only as a conditional resolver response, never authored or inferred by Hub.
