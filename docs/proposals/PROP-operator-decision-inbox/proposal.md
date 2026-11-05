---
id: PROP-operator-decision-inbox
title: Find pending delivery decisions across projects
summary: "Aggregate actionable PR questions and native SDD decisions with links to current owner-specific review and decision surfaces."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/delivery/
priority: medium
size: L
planning_effort: medium
dev_effort: high
milestone: MS-operator-decisions
boundaries:
  owns:
    - modules/hub/migrations/versions/
    - modules/hub/tests/integration/migrations/
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/tests/integration/features/project_management/pipeline_runs/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - modules/hub-ui/src/lib/components/
    - modules/hub-ui/src/routes/
    - docs/capabilities/delivery/
    - docs/capabilities/sdd/
    - docs/usecases/delivery/
    - docs/usecases/sdd/
    - docs/ux/delivery/
    - docs/ux/navigation/
    - docs/steering/
    - docs/architecture/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-operator-decision-inbox] Find pending delivery decisions across projects

## 1. Background & Hypothesis

`CAP-PR-operator-decisions`, `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` expose different question and approval subjects through run-specific surfaces. Operators must locate the relevant project/run before deciding. A cross-project decision worklist can provide one entry point while leaving each mutation with its owner.

### Source anchors

`modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.svelte`, `SddWorkflowRequests.svelte` and `SddRunPanel.svelte` provide the existing owner-specific decision surfaces. `UX-run-decisions` and `UX-sdd-workflow-request` describe their distinct meanings.

## 2. Technical Spike Findings

- Ordinary `RunQuestion` rows in `open` or `answered` state remain pending until application or dismissal. Native Hub questions use those shared rows but retain native owner controls; do not classify them as ordinary clarification.
- Native request and integration eligibility is persisted in `PipelineRun.sdd_progress`. It is evaluated evidence, not a live repository view. No per-native-request waiting timestamp exists. `materials/evidence.md` records the inspected source.
- A normalized read projection supports indexed cross-project pagination without evaluating each repository. One explicit review refresh is bounded to the selected owner.

## 3. Proposed Design & Impact

### Read projection and ownership

Use the decision in `PADR-decision-inbox-read-projection`. Add a rebuildable database discovery projection under the pipeline-run owner; native adapters supply native kinds and identities. Preserve the ordinary and native mutation APIs. No inbox mutation endpoint is introduced.

Each entry carries a stable owner key, project ID, run ID, kind, exact question/request ID, subject fingerprint, observed run revision, inspected head/base when available, title, waiting timestamp and its basis, and last evidence observation time. Kinds distinguish ordinary Run question, native Hub question, native worker question, native workflow request, native proposal decision and native integration decision. A native request `gate:dev-integration` produces only the integration kind; proposal acceptance and integration authority remain separate subjects. Include only registered answerable workflow request kinds; omit unsupported/unknown kinds rather than generating a generic action.

Define a pure native candidate extractor alongside the owner eligibility rules. Actionable entries require persisted paused/blocked run state and use snapshot provider, request data, holds, pending questions, approval and publication state. A recorded native worker answer retains a nonactionable Answer publication pending row during implementing until its answer envelope resolves the question; no second submission is enabled during publication. Failed publication remains owner recovery context rather than permission to replay a different answer. Do not implement a second approval predicate from UI display flags. A request held by another actionable question is represented as blocked context on the run's review surface, not a second actionable inbox row. An already-authorized integration or in-progress/published proposal decision is absent. Retain a worker question until its answer envelope resolves it, with an answer-recorded/waiting-for-publication label where that evidence exists. Decline/defer do not resolve requests.

Synchronize the projection in the same transaction as committed owner changes: question save/application/dismissal, run state/revision changes, native evidence replacement, proposal publication and approval/revocation. Keep first-observed time unchanged for the same subject fingerprint across evidence refreshes. A changed question, evidence head/base, workflow or runtime/policy identity, project binding, or request content creates a new native subject generation and resets its first-observed time. Close obsolete generations. Join current run/project records when listing so deleted/ended owners and inaccessible projects never leak through a retained projection row. Run deletion cascades discovery rows. No new retention policy or independent authorization ledger is created.

Bootstrap existing records from stored question rows and `sdd_progress` in bounded batches during migration/backfill. Ordinary waiting time is question creation time. Native waiting time is explicitly **First observed waiting**, initially the backfill time for pre-existing subjects; do not infer historical wait from Run `updated_at`. Unsupported/historical provider snapshots are excluded. Development tests bootstrap and transactional maintenance on SQLite and PostgreSQL. No repository/network evaluation occurs during backfill or listing.

### Listing contract

Provide a read-only authenticated pipeline-run API for cross-project discovery, with optional project, decision-kind and ordinary open/answered filters. Apply existing visibility/authority policy before selecting rows and validate filter ownership; do not invent project ACLs. Default page size 20, allowed 1–100. Sort oldest waiting first, then stable entry key. Return an opaque cursor bound to the normalized filter set and the last ordering tuple; reject malformed or mismatched cursors with 422. Fetch at most limit plus one rows; return `has_more` and `next_cursor`, with no exact total requirement.

This is keyset pagination of a changing worklist, not a frozen historical snapshot. Unchanged entries do not repeat across pages even when another entry closes. New or changed generations can appear before the cursor; Refresh restarts from the first page. Display that behavior. Keep waiting timestamp immutable per generation and distinguish ordinary exact age from native first-observed age. Include evidence freshness; never call listing evidence live.

### Review and navigation

Choose a dedicated Decisions screen linked from the existing application shell. It prioritizes the mixed worklist; a project-only list loses the cross-project outcome, and an action drawer duplicates owner controls. The Host collects any user preference on this recommendation; the worker assumes this arrangement within the authorized scope.

Selecting Review resolves the exact project/run/subject, loads current run/questions, and explicitly refreshes native repository evidence through a bounded owner inspection adapter. The readiness endpoint alone is insufficient: it does not persist the evidence basis used by subsequent mutation guards. The adapter inspects outside the database transaction, then compare-and-swaps the current run/project revision, epoch and binding before persisting refreshed evidence and discovery rows atomically. It preserves applicable `carry_decisions` and approval/revocation/publication fences; inspection never grants or revives authority. On a race, discard the inspection result and require Retry. Return the refreshed revision, evidence digest and exact subject generation. Do not overwrite concurrent answers, stops or publications. A plain GET run only reloads database state and does not establish fresh native evidence. The adapter performs no advance, dispatch, answer, approval, publication or merge. Reuse `RunDecisionsDialog`, `SddWorkflowRequests` and `SddRunPanel` after the refresh. Extend request selection so an exact non-first native request can be reviewed; never silently act on `requests[0]` instead. A missing, inaccessible, resolved, changed-generation or unsupported subject disables mutation, explains the change, refreshes the worklist and offers explicit reinspection. A newer generation requires a fresh Review action. The persisted replacement becomes reviewable on that explicit reinspection rather than looping against an obsolete evidence digest. Native refresh failures show Retry and keep all decision controls disabled. Owner mutation revision/head/authority checks remain required after refresh.

Closing review preserves filters, loaded page and focus on the originating row, or its nearest remaining neighbor. After a decision, requery the current page; saving an ordinary answer changes its label to Answer saved, not completion. Applying/dismissing it removes it. No list action itself resumes execution.

### Candidate acceptance examples

- **E1**: Given ordinary and native subjects from multiple visible projects, listing returns distinct kinds and exact owner identities; project filters cannot expose another project's data.
- **E2**: Given an ordinary open question, saving an answer keeps its entry as Answer saved; application or dismissal removes it. A native worker answer stays pending until the envelope resolves it.
- **E3**: Given a listed native subject whose head/request changed, Review refreshes the repository evidence and disables the old subject before any mutation; refresh errors also keep controls disabled.
- **E4**: Given more than 100 pending subjects, paging queries at most limit plus one rows, starts no execution and performs zero repository/provider calls; closing an earlier entry does not duplicate unchanged later entries.
- **E5**: Given two requests on a native run, selecting one opens that identity or explains why it cannot be answered; it never substitutes the first request.
- **E6**: Given pre-existing native evidence, bootstrap labels age First observed waiting from backfill; repeated same-subject refresh preserves that timestamp, and a changed generation resets it.
- **E7**: Given native proposal publication in progress, current approval, terminal owner, hidden project or held integration, that decision subject is absent while the appropriate blocking question remains discoverable. Native worker answer publication follows E9 instead.
- **E9**: Given a native worker answer is dispatched before envelope publication, its row remains visible as Answer publication pending with no answer controls; publication resolution removes it.
- **E10**: Given repository evidence changed or an inspection races an owner mutation, refresh either persists the current replacement basis under CAS or discards the stale result; explicit reinspection can review the replacement without dispatch or authority revival.
- **E8**: Given a conflict after refreshed inspection, the existing owner rejects the stale mutation; the inbox grants no authority and reinspection is required.

### Non-goals

- **Scope Excluded**: health dashboards, incident detection, quota queues, bulk approvals, SDK machine approvals, Jules provider questions and account approval.
- **Scope Excluded**: pilot operation, deployment, production verification, monitoring, operations guides and CI trigger changes.
- **Scope Excluded**: global counters, notifications, automatic answer application, new approval policy, historical native wait reconstruction and background repository polling for inbox freshness.

### Planning decisions and implementation checks

Use high Development effort because durable projection migration and cross-owner concurrency affect persisted state. Keep the proposal size L; this is one discovery outcome with one authority-preserving navigation path. Validate migration/backfill and owner lifecycle updates, PostgreSQL query plans/index use, permission filtering, cursor stability, exact-subject routing, refresh failure and stale races. Run relevant integration/UI tests, regenerate the typed UI API, then `just lint` and `just check` in Development. Planning executes document/envelope checks only; inspected tests do not establish passing application checks.

Boundaries include migration and architecture parents because the durable read projection changes persistence and component responsibility. Collection overlap with other Planning branches is future-only; partial code candidate coverage has no entrypoints and does not establish implementation independence. Development must recheck current branches and shared owner/UI edits before task boundaries are fixed.

## 4. Lifecycle & Retirement Criteria

Planning resolves the direction within the agreed operator-decision scope. The Host obtains plan-accept and proposal-handoff authority after reviewing committed evidence. This worker performs neither operation. Development reconciles the listed contracts and screens and verifies the accepted examples before integration. Optional separate UX review is user-authorized and recorded with this turn.
