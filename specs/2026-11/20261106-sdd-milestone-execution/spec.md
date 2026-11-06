---
id: SPEC-sdd-milestone-execution
title: Execute selected SDD milestone work sequentially
summary: Progress a durable selection of native SDD units sequentially while preserving dependency checks, approval boundaries and recoverable controls.
status: completed
created: 2026-11-06
depends_on:
  - SPEC-sdd-milestone-readiness
related_capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
  - CAP-EXEC-scheduling-maintenance
related_usecases:
  - UC-execute-sdd-batch
  - UC-start-sdd-activity
  - UC-complete-sdd-workflow
workflow: sdd-spec-feature
---

# [SPEC-sdd-milestone-execution] Execute selected SDD milestone work sequentially

## 1. Problem Statement & Motivation

Handed off from proposal PROP-sdd-milestone-execution on 2026-11-06.
- **Preserved Materials**: `docs/materials/2026-11/20261106-sdd-milestone-execution`
- Target Docs Blueprint: `PROP-sdd-milestone-execution-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

A project operator needs a durable selection that can advance successive native SDD units after closing the browser. `CAP-SDD-native-delivery` starts individual activities; it deliberately excludes milestone execution. `SPEC-sdd-milestone-readiness` supplies a bounded, pinned observation rather than execution authority. This proposal adds execution coordination while retaining existing per-activity PR owners.

#### Source anchors and prerequisite assumptions

`MAT-sdd-milestone-execution` records source inspection, incoming references and the option comparison. The original proposal of `SPEC-sdd-milestone-readiness` was accepted but unimplemented at the Planning base. The user authorized prerequisite order override for Planning only. Before Development/handoff, compare this design with its landed completed SPEC and replace the prerequisite through the normal canonical reference process. Acceptance of its proposal is not prerequisite completion. Do not invent the SPEC ID.

## 2. User Stories

- **US-1**: As an operator, I want an explicit durable sequential selection so that the existing native owners advance selected work after I close the browser.
- **US-2**: As an operator, I want revision-fenced future-admission controls and exact owner evidence so that uncertain effects never authorize another activity.

## 3. Non-Goals

- **Scope Excluded**: parallel members/batches, implicit approval, inferred dependencies, a second PR executor, automatic replacement, Work Item copies, SDK/vendor changes, deployment and live verification.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] ME-01

Given complete pinned preview evidence with A and dependency-held B, when explicitly selected, then a durable ordered selection contains exactly A/B with their future-intent labels. No work/gates are approved by selection. Incomplete/unknown/over-limit input and stale SHA cause zero admission calls. Include 50/51, 200/201 and 500/501 boundary fixtures.

### [AC-02] ME-02

Given done/dropped milestone prerequisites and exact completed SPEC prerequisites, when the next entry is evaluated, then they pass without reopening completed history. Accepted/rejected PROP, missing/ambiguous/cyclic anchors and guessed same-slug lineage hold. Test canonical handoff repair and missing deleted PROP separately; assert dependency evaluation invokes no publication collaborator.

### [AC-03] ME-03

Given draft A then B, when A reaches a worker report, accepted-but-unmerged Planning, merged Planning, handoff and completed-but-unmerged Development, then no premature next member starts. Only exact completed SPEC plus owner-confirmed Development merge releases its slot. Existing ask gates and withdrawn approvals remain effective at every phase. Cover normal A-to-B progression after A's exact owner-confirmed handoff removes its direct proposal membership.

### [AC-04] ME-04

Given concurrent ticks/controls/single starts, when the claim and pause/stop race, then exactly one committed admission identity wins, one slot remains occupied and control ordering matches the linearization point. PostgreSQL multi-connection barriers cover both orders, stale leases and expired-worker recovery.

### [AC-05] ME-05

Given failure after claim, branch creation, PR creation or enrollment and loss of each database response, when reconciled, then the same claim/artifacts/run are recovered or held with exact uncertainty; no later member, replacement branch or duplicate PR/run is created. Include branch-only recovery and unrelated branch/marker spoof/cross-project evidence refusals.

### [AC-06] ME-06

Given base drift during evaluation or before native creation, when admission runs, then it uses one evaluated SHA or refuses/retries. Unrelated/confirmed selected merges re-evaluate; membership/scope/runtime/policy changes hold. Canonical dependency repair is accepted only by the bounded comparison rule. An expected admitted-member handoff removal advances only with exact recorded lineage and selected owner merge; an unadmitted removal holds. A missing unadmitted proposal never becomes a guessed spec.

### [AC-07] ME-07

Given paused/stopped batches and replayed requests, when controls or maintenance run, then no prohibited future claim occurs and no native approval/control changes. An earlier admitted effect remains honestly visible. A stopped batch with unresolved work prevents a second active batch until settlement.

### [AC-08] ME-08

Given reload, late responses and project changes, when the operator opens the batch, then durable identity/order/holds/control revisions restore without reverting newer controls. Failed/stopped/partial outcomes never display full completion. Read-only links inspect existing native owners.

### [AC-09] ME-09

Given pending batches and retention/maintenance work, when bounded ticks/pruning run, then fair bounded progress and failure isolation hold; unresolved PR/run links survive pruning or retain an explicit durable outcome tombstone after settlement. No new scheduler/merge owner is created.

### [AC-10] ME-10

Given unauthorized/non-SDD/rebound projects or unsafe paths, when create/get/control runs, then existing access/lifecycle/runtime restrictions apply before effects. Individual starts, proposal decisions and native CI/merge regression tests remain green.

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Technical Spike Findings

- **Q1 resolved**: Retain an immutable execution selection and separate current evaluations. Pin creation to project/repository, base ref/full SHA, milestone ID/path, complete discovery and exact member/dependency anchors. A preview response is no authority token.
- **Q2 resolved**: One selected member retains the sequential slot through Planning, its decision/merge, handoff-first Development and final owner-confirmed merge/completed SPEC. Every transition retains existing approvals and fresh native admission. Rejected, canceled or failed work stops automatic progression pending operator inspection.
- **Q3 resolved**: Persist admission intent before remote effects. Serialize claim and control under revision fences. Recover the same branch/PR/run using exact ownership evidence. Unknown outcomes retain the slot; they never permit replacement work.

### 3. Proposed Design & Impact

#### Planning decisions

`ADR-sdd-batch-ledger` records the ledger/owner boundary. Development effort remains high for persisted state and concurrency.

1. **Explicit chain selection**: Add an execution-specific selection beside the preview. It may contain complete, supported direct draft/accepted proposal members whose only current scheduling hold is an unfinished exact prerequisite. This is explicit future intent, not eligibility. Eligible-only batches would prevent selecting a milestone chain; that alternative is not recommended. Preserve the predecessor's read-only eligible-only subset unchanged. Clearly label waiting entries and missing external prerequisites. Never silently include prerequisite members. Exclude reviewing/rejected, existing activity, unsupported, workflow-held, unknown or incomplete rows from new batch selection. A selected chain may wait on external prerequisites; disclose them before confirmation.
2. **Creation**: `POST /api/v1/projects/{project_id}/sdd/batches` accepts UUID request identity, expected preview SHA, milestone identity/path, exact selected member IDs/paths, proposed initial activity kinds, explicit through-Development intent and optional per-activity effort/catalog preferences. The server recomputes complete discovery/evidence at the current selected ref. Any SHA change between preview and creation refuses with HTTP 409; incomplete, ambiguous, cyclic, malformed or unsafe input refuses before admission. Bound selection to the predecessor's 50 members/200 anchors/500 edges and request budget. Persist the deterministic topological order with canonical-ID tie breaking. Empty selection is invalid. Matching request/actor/payload replays current state; changed actor/payload conflicts. Creation persists intent and does not itself approve any gate.
3. **Ledger and exclusion**: Add SDD-owned batch, member, admission-attempt and control-receipt records. Retain original identities, immutable ordered selection, dependency source/graph, creation SHA/runtime/config/policy, latest evaluated SHA/digest/time, current phase, exact proposal/spec lineage, branch/PR/run links and durable outcomes. Use one nonterminal batch per project. A paused or stopped batch with an unsettled admitted activity retains that exclusion. One member/activity claim holds the batch slot. Do not store copies of proposal/spec bodies or Work Items. Project access applies to every read/control; another project's matching slug/PR is never evidence.
4. **Fresh admission**: Before each Planning start, Development start and handoff continuation, resolve the same base ref to a full SHA; read all repository scheduling facts at that SHA; evaluate exact dependencies, workflow holds, lifecycle, runtime/config/policy and current project/catalog/branch ownership through existing evaluators. Scheduling is an additional batch constraint and changes no individual-start contract. Milestone prerequisites pass when done OR dropped. A direct unit prerequisite passes only when its exact canonical ID resolves to one completed SPEC. Never traverse a completed SPEC's own prerequisites. Draft/reviewing/accepted/rejected PROP prerequisites remain held. Matching slugs and `handoff_from` are inspection links, not canonical dependency resolution.
5. **Progression and identity**: A draft selected member first runs Planning. The same slot waits for existing plan-accept authority and the Planning PR owner's confirmed merge into the selected base; a finished worker or accepted status on an unmerged branch is insufficient. Fresh accepted base evidence permits handoff-first Development only under the applicable proposal-handoff gate. An initially accepted member starts there. Record the exact resulting SPEC from the admitted native run's validated handoff transition, not by scanning for similar names. Final member success needs that exact completed SPEC on the selected base plus the linked Development PR owner's confirmed merged result/merge SHA. Closed-unmerged, rejected, canceled and failed outcomes hold the batch; completed batch means every selected member succeeded. Stop explicitly leaves unadmitted members unexecuted, never succeeded.
6. **Deleted anchors and dependency repairs**: Preserve a batch member's exact original PROP and its validated activity-to-SPEC lineage after handoff deletes the proposal. This permits following that already-admitted member, not satisfying another member's PROP dependency. On the next evaluation, an explicit canonical PROP alias/mapping to the completed SPEC may satisfy the edge. Otherwise the edge is repair-needed, even when the ledger knows which run performed the handoff. Show the original/current anchor and required repository reference repair. A missing unadmitted member is held, never silently skipped or replaced. The batch only observes and validates edge-only repairs published by an existing devkit handoff/native PR owner or an independently operator-authorized repository change. The coordinator never authors, commits or pushes these repairs. Absent an exact canonical mapping or published repair, the entry remains repair-needed. Observation of canonical dependency-reference repair on the base is permitted after comparison proves it changes only that edge to the exact completed SPEC and preserves the selected member's identity, scope and other inputs; retain old/new edge evidence. Any other content change requires stop and a new selection. This allows honest chain continuation without guessing lineage.
7. **Selected-base drift**: Before committing a claim, compare the fresh basis to the ledger revision and re-read remote base head. If it moved again, discard evaluation and retry within the budget. Removal or lifecycle transformation of an already-admitted selected member is permitted only when recorded native lineage and a confirmed selected PR merge prove that exact expected transition. Preserve original immutable membership in the ledger. Additions, removal of unadmitted members and all unexplained membership changes hold admission. A ref deletion, repository rebinding, remaining-member scope/content, dependency graph beyond proven canonical repair, runtime/config/policy or unknown ancestry holds future admission. Unrelated base commits and confirmed earlier selected merges may advance the checkpoint after fresh full evaluation. Retain comparison evidence; do not silently adopt newly added members. A policy change never upgrades authority and leaves native approval invalidation with its existing owner. Changed selection requires stop and a new batch; no in-place membership editing or blanket approval refresh.
8. **Claim/control fence**: Under Project then Batch row locks, verify current project/batch revisions and nonterminal runnable state, persist one stable admission identity and reserve the slot before calling native admission. This committed claim is the admission linearization point. Recheck evaluated project/config identity and base precondition immediately before branch creation; enhance the internal ActivityStarter seam with an expected base SHA rather than silently refetching a different head. The native branch is created from that evaluated immutable SHA. A base move afterward is reported by the next observation and existing native reintegration checks. Concurrent single-start and batch-start of the same activity serialize through a shared project/unit/activity reservation; they may attach only the same proven owner. Never enroll a preexisting unrelated run merely because its slug matches.
9. **Recovery**: Retain branch, initial commit, activity marker, PR number and enrollment receipt as each becomes known. Crash before branch effect retries the same claim after reconciliation. Branch exists without PR: resume only when the recorded initial commit and exact owned branch match; create the missing PR once. PR exists without run: reconcile marker/repository/base/head plus saved claim, then use existing idempotent enrollment. Lost enrollment result reconciles its exact project/PR run before another call. An ambiguous or unavailable remote result holds `recovering`; no later member starts. Partial effects are visible and retained. Never force-push, overwrite unrelated branches, delete artifacts or claim exactly-once remote effects. Apply the same durable reservation path to individual starts where needed to close the cross-entry race, preserving their API/admission behavior.
10. **Controls and driver**: List/get batch endpoints expose evidence and read-only owner links. `POST .../batches/{id}/controls` accepts UUID request identity, expected revision and one of pause/resume/stop. HTTP 409 covers stale revision or receipt mismatch; HTTP 422 covers invalid controls/selection. Pause/stop that commits before claim prevents it. If claim commits first, that activity is admitted and may still create external artifacts after the control response; show it as in flight. Controls do not cancel, resume or approve that native run. Resume re-evaluates waits and future admission; stop is terminal for future claims. Matching receipts return current state without undoing a later stop. Maintenance selects a bounded page of due batches with persisted fair cursor, one reconciliation/admission transition per selected batch per tick, within its existing timeout. Reuse PR-owner observation, never CI/merge logic. Retry transport uncertainty by reconciliation of the same claim; terminal native failure requires operator inspection, not automatic replacement. Protect unresolved batch links/outcomes from run retention until a durable completion tombstone is recorded; active, paused and uncertain work must remain inspectable.

#### Acceptance criteria for Development

- **ME-01**: Given complete pinned preview evidence with A and dependency-held B, when explicitly selected, then a durable ordered selection contains exactly A/B with their future-intent labels. No work/gates are approved by selection. Incomplete/unknown/over-limit input and stale SHA cause zero admission calls. Include 50/51, 200/201 and 500/501 boundary fixtures.
- **ME-02**: Given done/dropped milestone prerequisites and exact completed SPEC prerequisites, when the next entry is evaluated, then they pass without reopening completed history. Accepted/rejected PROP, missing/ambiguous/cyclic anchors and guessed same-slug lineage hold. Test canonical handoff repair and missing deleted PROP separately; assert dependency evaluation invokes no publication collaborator.
- **ME-03**: Given draft A then B, when A reaches a worker report, accepted-but-unmerged Planning, merged Planning, handoff and completed-but-unmerged Development, then no premature next member starts. Only exact completed SPEC plus owner-confirmed Development merge releases its slot. Existing ask gates and withdrawn approvals remain effective at every phase. Cover normal A-to-B progression after A's exact owner-confirmed handoff removes its direct proposal membership.
- **ME-04**: Given concurrent ticks/controls/single starts, when the claim and pause/stop race, then exactly one committed admission identity wins, one slot remains occupied and control ordering matches the linearization point. PostgreSQL multi-connection barriers cover both orders, stale leases and expired-worker recovery.
- **ME-05**: Given failure after claim, branch creation, PR creation or enrollment and loss of each database response, when reconciled, then the same claim/artifacts/run are recovered or held with exact uncertainty; no later member, replacement branch or duplicate PR/run is created. Include branch-only recovery and unrelated branch/marker spoof/cross-project evidence refusals.
- **ME-06**: Given base drift during evaluation or before native creation, when admission runs, then it uses one evaluated SHA or refuses/retries. Unrelated/confirmed selected merges re-evaluate; membership/scope/runtime/policy changes hold. Canonical dependency repair is accepted only by the bounded comparison rule. An expected admitted-member handoff removal advances only with exact recorded lineage and selected owner merge; an unadmitted removal holds. A missing unadmitted proposal never becomes a guessed spec.
- **ME-07**: Given paused/stopped batches and replayed requests, when controls or maintenance run, then no prohibited future claim occurs and no native approval/control changes. An earlier admitted effect remains honestly visible. A stopped batch with unresolved work prevents a second active batch until settlement.
- **ME-08**: Given reload, late responses and project changes, when the operator opens the batch, then durable identity/order/holds/control revisions restore without reverting newer controls. Failed/stopped/partial outcomes never display full completion. Read-only links inspect existing native owners.
- **ME-09**: Given pending batches and retention/maintenance work, when bounded ticks/pruning run, then fair bounded progress and failure isolation hold; unresolved PR/run links survive pruning or retain an explicit durable outcome tombstone after settlement. No new scheduler/merge owner is created.
- **ME-10**: Given unauthorized/non-SDD/rebound projects or unsafe paths, when create/get/control runs, then existing access/lifecycle/runtime restrictions apply before effects. Individual starts, proposal decisions and native CI/merge regression tests remain green.

#### Implementation and verification outline

Keep Router → UseCase → Service → Repository. Add persistence/migrations and coordination in the existing SDD feature, an expected-base admission seam, shared same-activity reservation, maintenance hook and typed API/client/UI components. Keep feature dependencies within declared project-management/execution ownership; any needed new architecture declaration must be surfaced before Development rather than silently widening scope.

Initialize the backend environment, regenerate the API client with `just gen-ui-api`, run focused SDD activity/lineage/approval/recovery suites, PostgreSQL locking and migration round-trip coverage, UI selection/control integration tests, `just lint` and `just check`. Planning verifies documents only; no product test execution or deployed result is claimed. No timing improvement is claimed. For count assertions, Development measures its head with the batch feature disabled as the baseline; workers never check out another head.

#### Non-goals

- **Scope Excluded**: Parallel batches, parallel selected members, implicit gates, a second CI/merge owner, Work Plan/specification copies, inferred dependencies, automatic failed-work replacement and silently expanding selection.
- **Scope Excluded**: Existing independent-spec enrollment from the preview, modifying devkit semantics, vendor UI changes, SDK flows, pilot operation, deployment, production verification, monitoring and CI trigger changes.

### 4. Lifecycle & Retirement Criteria

This turn recommends explicit future-intent chain selection and a separate immutable execution ledger. It records no plan-accept or handoff. The Host must compare the provisional readiness contract with its landed exact completed SPEC before Development/handoff and present the execution-selection extension at plan-accept. `SPEC-sdd-milestone-readiness` remains a true prerequisite; Planning order override does not weaken it. Challenger round 1 returned two P2 clarifications, folded by its concrete wording actions and closed by reverify. The separate UX reviewer returned one preference-visibility finding; its exact content/edit/confirmation action is folded into the screen draft. The original UX finding remains open for presentation at plan-accept under the Planning UX procedure. Required findings and checks are retained in this bundle. No unresolved business choice requires a question round.

