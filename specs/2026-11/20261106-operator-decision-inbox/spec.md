---
id: SPEC-operator-decision-inbox
title: Find pending delivery decisions across projects
summary: Aggregate actionable PR questions and native SDD decisions with links to current owner-specific review and decision surfaces.
status: completed
created: 2026-11-06
related_capabilities: [CAP-PR-operator-decisions, CAP-SDD-native-delivery, CAP-SDD-workflow-control]
related_usecases: [UC-resolve-run-question, UC-decide-sdd-proposal, UC-complete-sdd-workflow]
workflow: sdd-spec-feature
---

# [SPEC-operator-decision-inbox] Find pending delivery decisions across projects

## 1. Problem Statement & Motivation

Handed off from proposal PROP-operator-decision-inbox on 2026-11-06.
- **Preserved Materials**: `docs/materials/2026-11/20261106-operator-decision-inbox`
- Target Docs Blueprint: `PROP-operator-decision-inbox-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

`CAP-PR-operator-decisions`, `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` expose different question and approval subjects through run-specific surfaces. Operators must locate the relevant project/run before deciding. A cross-project decision worklist can provide one entry point while leaving each mutation with its owner.

#### Source anchors

`modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.svelte`, `SddWorkflowRequests.svelte` and `SddRunPanel.svelte` provide the existing owner-specific decision surfaces. `UX-run-decisions` and `UX-sdd-workflow-request` describe their distinct meanings.

## 2. User Stories

- **US-1**: As an operator, I want to discover pending decisions across visible projects and review the exact owner subject.
- **US-2**: As an operator, I want refreshed native evidence and explicit stale-subject feedback before submitting a decision.

## 3. Non-Goals

1. **Scope Excluded**: Bulk approvals, automatic application, new authority policy, background repository polling, SDK/Jules questions, notifications, deployment and operations changes.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Mixed discovery
- **Given** visible projects contain ordinary and supported native decisions
- **When** the authenticated operator lists decisions
- **Then** entries retain exact owner identities and distinct supported kinds; inaccessible or terminal owners are absent.

### [AC-02] Owner lifecycle
- **Given** an ordinary question is open
- **When** an answer is saved and later applied or dismissed
- **Then** saving retains Answer saved; application or dismissal removes the entry transactionally.

### [AC-03] Bounded pagination
- **Given** more than 100 pending subjects exist
- **When** pages are requested with limits 1 through 100
- **Then** the query fetches at most limit plus one ordered rows, makes zero provider calls, and malformed or filter-mismatched cursors return 422.

### [AC-04] Generation age
- **Given** native subjects exist before migration
- **When** backfill and repeated refreshes run
- **Then** native age uses First observed waiting; the same fingerprint preserves age and a changed generation resets it; ordinary age uses question creation.

### [AC-05] Exact native review
- **Given** a run has multiple native requests
- **When** Review selects a non-first subject
- **Then** bounded inspection persists current evidence under revision/epoch/binding CAS before controls enable, and never substitutes another request.

### [AC-06] Stale review and races
- **Given** the listed subject changed or inspection races an owner mutation
- **When** Review refreshes evidence
- **Then** stale inspection is discarded, controls remain disabled, and explicit reinspection can review the replacement without authority revival.

### [AC-07] Publication and authority
- **Given** native worker answer publication is pending or proposal/integration authority exists
- **When** the inbox is listed
- **Then** worker publication retains a nonactionable row until exact resolution; already-authorized integration and in-progress/published proposal decisions are absent.

### [AC-08] Owner navigation
- **Given** the operator filters and pages the inbox
- **When** Review opens and closes or completes an owner decision
- **Then** existing owner controls preserve guards, filters and loaded page persist, focus returns to the originating row or nearest neighbor, and the current page reloads after a decision.

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Technical Spike Findings

- Ordinary `RunQuestion` rows in `open` or `answered` state remain pending until application or dismissal. Native Hub questions use those shared rows but retain native owner controls; do not classify them as ordinary clarification.
- Native request and integration eligibility is persisted in `PipelineRun.sdd_progress`. It is evaluated evidence, not a live repository view. No per-native-request waiting timestamp exists. `docs/materials/2026-11/20261106-operator-decision-inbox/evidence.md` records the inspected source.
- A normalized read projection supports indexed cross-project pagination without evaluating each repository. One explicit review refresh is bounded to the selected owner.

### 3. Proposed Design & Impact

#### Read projection and ownership

Use the decision in `ADR-decision-inbox-read-projection`. Add a rebuildable database discovery projection under the pipeline-run owner; native adapters supply native kinds and identities. Preserve the ordinary and native mutation APIs. No inbox mutation endpoint is introduced.

Each entry carries a stable owner key, project ID, run ID, kind, exact question/request ID, subject fingerprint, observed run revision, inspected head/base when available, title, waiting timestamp and its basis, and last evidence observation time. Kinds distinguish ordinary Run question, native Hub question, native worker question, native workflow request, native proposal decision and native integration decision. A native request `gate:dev-integration` produces only the integration kind; proposal acceptance and integration authority remain separate subjects. Include only registered answerable workflow request kinds; omit unsupported/unknown kinds rather than generating a generic action.

Define a pure native candidate extractor alongside the owner eligibility rules. Actionable entries require persisted paused/blocked run state and use snapshot provider, request data, holds, pending questions, approval and publication state. A recorded native worker answer retains a nonactionable Answer publication pending row during implementing until its answer envelope resolves the question; no second submission is enabled during publication. Failed publication remains owner recovery context rather than permission to replay a different answer. Do not implement a second approval predicate from UI display flags. A request held by another actionable question is represented as blocked context on the run's review surface, not a second actionable inbox row. An already-authorized integration or in-progress/published proposal decision is absent. Retain a worker question until its answer envelope resolves it, with an answer-recorded/waiting-for-publication label where that evidence exists. Decline/defer do not resolve requests.

Synchronize the projection in the same transaction as committed owner changes: question save/application/dismissal, run state/revision changes, native evidence replacement, proposal publication and approval/revocation. Keep first-observed time unchanged for the same subject fingerprint across evidence refreshes. A changed question, evidence head/base, workflow or runtime/policy identity, project binding, or request content creates a new native subject generation and resets its first-observed time. Close obsolete generations. Join current run/project records when listing so deleted/ended owners and inaccessible projects never leak through a retained projection row. Run deletion cascades discovery rows. No new retention policy or independent authorization ledger is created.

Bootstrap existing records from stored question rows and `sdd_progress` in bounded batches during migration/backfill. Ordinary waiting time is question creation time. Native waiting time is explicitly **First observed waiting**, initially the backfill time for pre-existing subjects; do not infer historical wait from Run `updated_at`. Unsupported/historical provider snapshots are excluded. Development tests bootstrap and transactional maintenance on SQLite and PostgreSQL. No repository/network evaluation occurs during backfill or listing.

#### Listing contract

Provide a read-only authenticated pipeline-run API for cross-project discovery, with optional project, decision-kind and ordinary open/answered filters. Apply existing visibility/authority policy before selecting rows and validate filter ownership; do not invent project ACLs. Default page size 20, allowed 1–100. Sort oldest waiting first, then stable entry key. Return an opaque cursor bound to the normalized filter set and the last ordering tuple; reject malformed or mismatched cursors with 422. Fetch at most limit plus one rows; return `has_more` and `next_cursor`, with no exact total requirement.

This is keyset pagination of a changing worklist, not a frozen historical snapshot. Unchanged entries do not repeat across pages even when another entry closes. New or changed generations can appear before the cursor; Refresh restarts from the first page. Display that behavior. Keep waiting timestamp immutable per generation and distinguish ordinary exact age from native first-observed age. Include evidence freshness; never call listing evidence live.

#### Review and navigation

Choose a dedicated Decisions screen linked from the existing application shell. It prioritizes the mixed worklist; a project-only list loses the cross-project outcome, and an action drawer duplicates owner controls. The Host collects any user preference on this recommendation; the worker assumes this arrangement within the authorized scope.

Selecting Review resolves the exact project/run/subject, loads current run/questions, and explicitly refreshes native repository evidence through a bounded owner inspection adapter. The readiness endpoint alone is insufficient: it does not persist the evidence basis used by subsequent mutation guards. The adapter inspects outside the database transaction, then compare-and-swaps the current run/project revision, epoch and binding before persisting refreshed evidence and discovery rows atomically. It preserves applicable `carry_decisions` and approval/revocation/publication fences; inspection never grants or revives authority. On a race, discard the inspection result and require Retry. Return the refreshed revision, evidence digest and exact subject generation. Do not overwrite concurrent answers, stops or publications. A plain GET run only reloads database state and does not establish fresh native evidence. The adapter performs no advance, dispatch, answer, approval, publication or merge. Reuse `RunDecisionsDialog`, `SddWorkflowRequests` and `SddRunPanel` after the refresh. Extend request selection so an exact non-first native request can be reviewed; never silently act on `requests[0]` instead. A missing, inaccessible, resolved, changed-generation or unsupported subject disables mutation, explains the change, refreshes the worklist and offers explicit reinspection. A newer generation requires a fresh Review action. The persisted replacement becomes reviewable on that explicit reinspection rather than looping against an obsolete evidence digest. Native refresh failures show Retry and keep all decision controls disabled. Owner mutation revision/head/authority checks remain required after refresh.

Closing review preserves filters, loaded page and focus on the originating row, or its nearest remaining neighbor. After a decision, requery the current page; saving an ordinary answer changes its label to Answer saved, not completion. Applying/dismissing it removes it. No list action itself resumes execution.

#### Candidate acceptance examples

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

#### Non-goals

- **Scope Excluded**: health dashboards, incident detection, quota queues, bulk approvals, SDK machine approvals, Jules provider questions and account approval.
- **Scope Excluded**: pilot operation, deployment, production verification, monitoring, operations guides and CI trigger changes.
- **Scope Excluded**: global counters, notifications, automatic answer application, new approval policy, historical native wait reconstruction and background repository polling for inbox freshness.

#### Planning decisions and implementation checks

Use high Development effort because durable projection migration and cross-owner concurrency affect persisted state. Keep the proposal size L; this is one discovery outcome with one authority-preserving navigation path. Validate migration/backfill and owner lifecycle updates, PostgreSQL query plans/index use, permission filtering, cursor stability, exact-subject routing, refresh failure and stale races. Run relevant integration/UI tests, regenerate the typed UI API, then `just lint` and `just check` in Development. Planning executes document/envelope checks only; inspected tests do not establish passing application checks.

Boundaries include migration and architecture parents because the durable read projection changes persistence and component responsibility. Collection overlap with other Planning branches is future-only; partial code candidate coverage has no entrypoints and does not establish implementation independence. Development must recheck current branches and shared owner/UI edits before task boundaries are fixed.

### 4. Lifecycle & Retirement Criteria

Planning resolves the direction within the agreed operator-decision scope. The Host obtains plan-accept and proposal-handoff authority after reviewing committed evidence. This worker performs neither operation. Development reconciles the listed contracts and screens and verifies the accepted examples before integration. Optional separate UX review is user-authorized and recorded with this turn.


## 6. Screens

### Candidates and recommendation

- **A — dedicated Decisions screen, recommended**: a mixed oldest-waiting worklist is primary and each Review action opens the owner dialog. This supports cross-project triage with one navigation entry.
- **B — decision grouping inside each project**: preserves current navigation but requires visiting projects and does not meet cross-project discovery without another surface.
- **C — worklist with inline action drawer**: keeps a continuous list but introduces a second composition of authority-sensitive controls and competes with the existing owner review surfaces.

Proceed with A as the within-scope Planning assumption. The Host offers this comparison for user preference and has obtained opt-in for a separate UX review.

### UX-decision-inbox — Decision inbox (screen draft)

- **Area/element**: delivery / screen.
- **Use cases**: `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`.
- **Capabilities**: `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`.

#### Purpose

- **Primary task**: Find a pending decision and open its current review context.
- **Facts to commit**: Project/run, explicit decision kind, question/request identity, saved-versus-applied state, evidence head and observation time, and waiting-age basis.
- **Secondary items**: Decision editors and complete evidence remain in `UX-run-decisions` and its native panels; history stays with the owner.

#### Content

The filtered mixed worklist is primary. Filters sit above it, and cursor navigation sits below. No approve/resume control appears in a row.

- Project connection (all-visible-projects default; optional project filter).
- Run question / Native SDD activity (kind filter and ordinary open/answered filter).
- PR run (row project, run/PR link and state).
  - Run question (title, question ID, Needs answer or Answer saved; exact waiting age).
  - Native SDD activity (request kind/title/identity, First observed waiting age, evidence head, last inspected time; Answer publication pending as a disabled review-only status while its worker envelope is being published).
  - Review (opens exact owner subject after freshness verification).
- Pagination (Next; loaded previous cursor pages; Refresh restarts at first page).
- Application shell (global navigation to other screens).

#### States

- **loading**: Explain that pending decisions are loading; filters/navigation remain accessible, Review waits for data.
- **populated**: Review any row; distinguish native observation age from ordinary waiting age. Explain that new or changed decisions can precede the current cursor and Refresh restarts the list.
- **empty**: No matching observed pending decisions; offer Clear filters and Refresh. This does not assert that every repository is live-evaluated.
- **error**: Keep filters and offer Retry; no stale row becomes actionable from the failure.
- **reviewing**: Owner dialog loads fresh context; all mutation controls disabled until exact subject validation succeeds.
- **changed**: Subject resolved, changed or unavailable; explain the outcome, refresh the worklist and offer explicit Review again for any replacement.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Review ordinary question | `UC-resolve-run-question` 1 | populated | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | Exact question and current revision load; old question cannot be substituted. |
| Review native Run question | `UC-complete-sdd-workflow` 3d | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact Hub question loads with native answer/application behavior. |
| Review proposal decision | `UC-decide-sdd-proposal` 1 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-native-delivery` | Current native evidence loads before proposal controls enable. |
| Review worker/workflow request | `UC-complete-sdd-workflow` 3b, 3c | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact request is selected in `UX-sdd-workflow-request`; missing identity requires reinspection. |
| Review integration decision | `UC-complete-sdd-workflow` 4 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | `UX-sdd-run` receives refreshed evidence and preserves approval fences. |
| Change filters | global: narrow discovery without deciding | populated | loading | | | Cursor resets; only matching visible subjects load. |
| Next / Previous | global: browse observed pending decisions | populated | loading | | | Current filters persist; unavailable cursor navigation is disabled. |
| Refresh / Retry / Clear filters | global: recover discovery | error, empty, populated | loading | | | First page reloads with selected filters or cleared filters. |
| Close owner dialog | global: return from inspection | reviewing, changed | populated | close | | Filters/page persist; focus returns to row or nearest remaining neighbor. |
| Leave Decisions | global: navigate to another task | populated, empty, error | populated | `UX-app-shell` | | Selected destination opens. |

### Review follow-up

The first separate UX review found a missing native Hub question route and undrafted register rows. Both are folded above. Its original findings remain recorded for the Host at plan-accept; Development closes them against retained screens and implementation. No prototype/browser validation is claimed.

### Owner surface amendments

`UX-run-decisions` adds selected question/request identity and a disabled loading state. After refresh, a changed subject never inherits an editor selection or typed approval from the old subject. Failed refresh offers Retry and Close. A successful save shows Answer saved and keeps the inbox entry; applying/dismissing removes it. Native controls retain all existing confirmation/reason requirements and owner errors. Closing restores the inbox state and focus. Reuse the same owner dialog reached from per-run lists.
