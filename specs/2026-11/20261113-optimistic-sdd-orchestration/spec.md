---
id: SPEC-optimistic-sdd-orchestration
title: Delegate SDD execution to repositories and agents
summary: "Remove Hub-side SDD runtime preparation and workflow evaluation, start work through ordinary PR delivery and observe repository-owned GitHub Actions checks."
status: in-progress
created: 2026-11-13
related_capabilities: [CAP-SDD-native-delivery, CAP-SDD-workflow-control, CAP-SDD-runtime-isolation, CAP-SDK-existing-pr-bridge, CAP-PR-pull-request-delivery, CAP-PR-operator-decisions]
related_usecases: [UC-start-sdd-activity, UC-complete-sdd-workflow, UC-decide-sdd-proposal, UC-preview-sdd-milestone, UC-execute-sdd-batch]
workflow: sdd-spec-feature
---

# [SPEC-optimistic-sdd-orchestration] Delegate SDD execution to repositories and agents

## Problem Statement

Hub's embedded devkit evaluator makes repository tooling and internal workflow
correctness prerequisites of orchestration. `ADR-repository-owned-sdd-execution`
changes that responsibility: the repository and agent own setup and execution;
Hub owns PR delivery, human input, GitHub CI observation and merge controls.
The approved source proposal is retained in Git at the Planning merge.

## User Stories

- As an operator, I can request repository work without provisioning its devkit runtime in Hub.
- As an operator, I can answer agent questions and follow current-head CI through the ordinary PR Run.
- As an operator, I can inspect old native execution evidence without reviving its retired authority.

## Non-Goals

- **Scope Excluded**: replacement evaluator, remote runner, GitHub Action or sync service.
- **Scope Excluded**: reimplementing devkit gates or adding an alternative batch/bridge system.
- **Scope Excluded**: changing Work Plans, provider adapters, generic SDK runtime or Auto Hub's contributor SDD.
- **Scope Excluded**: deleting historical runs, decisions, selections, attempts or PR links.

## Acceptance Criteria

### [AC-01] Repository tools are not admission prerequisites

- **Given** an enabled connected SDD project and a repository without devkit lock, receipt or compatible Python.
- **When** an authorized operator starts Planning or Development.
- **Then** Hub creates the Draft activity PR and Run without runtime setup or repository workflow evaluation.

### [AC-02] Repository eligibility belongs to the agent

- **Given** a requested proposal with arbitrary status, size or prerequisites.
- **When** the activity starts.
- **Then** Hub validates only access, input, GitHub refs and exclusive ownership; no SDD eligibility refusal is produced.

### [AC-03] Recover exact activity artifacts

- **Given** a start whose branch/PR publication response is lost.
- **When** the same request is retried.
- **Then** the original claim, exact branch, Draft PR and Run are recovered without duplicate effects or proposal-state edits.

### [AC-04] Repository-owned execution instructions

- **Given** a new optimistic activity Run with unit and effort intent.
- **When** an implementation attempt is dispatched.
- **Then** instructions follow the repository without a current devkit stage, single-stage stop, sync prescription or Hub-authored workflow decisions.

### [AC-05] Questions around pushes retain operator control

- **Given** an agent posts a correlated question before or after pushing on the active attempt.
- **When** Hub observes implementation or CI progress.
- **Then** the question pauses delivery before merge; saving an answer grants neither resume nor ready/merge status.

### [AC-06] Ordinary GitHub CI and merge boundaries

- **Given** an agent push with no open question.
- **When** CI is observed and the operator marks the PR ready.
- **Then** existing current-head checks and project policy govern merge; Draft and moved-head rechecks continue to prevent merging.

### [AC-07] No embedded evaluator path

- **Given** the application, workers and MCP are loaded.
- **When** retained APIs execute or removed UI surfaces render.
- **Then** no devkit execution, local repository checkout, runtime install, source build or workflow interpretation is reachable.

### [AC-08] Legacy authority is fenced

- **Given** nonterminal native Runs, batches, claims and stale worker credentials exist.
- **When** the migration or legacy controls run.
- **Then** history is preserved, local progression ends, legacy resume returns 410 SDD_EXECUTION_RETIRED, and uncertain prior ownership needs explicit reconciliation before new work.

### [AC-09] SDK bridge retirement is durable

- **Given** legacy built-in bridge bindings and ordinary SDK flows exist.
- **When** registration, start or worker progression is attempted.
- **Then** synchronous new bridge effects return 410 SDD_BRIDGE_RETIRED; undispatched work is durably retired, outstanding no-receipt work fails terminally, and receipt-backed work only observes its existing owner.

### [AC-10] History remains browsable

- **Given** an available historical unit, Run, batch or decision is selected.
- **When** the operator opens its retained link.
- **Then** the exact available subject is displayed read-only with retired status and without runtime/readiness probes or live native controls.

### [AC-11] Serving image needs no SDD environment

- **Given** the image and contributor check recipes are prepared.
- **When** they are inspected and ordinary checks run.
- **Then** no evaluator build/cache/sandbox/source credential is required while Auto Hub contributor devkit setup continues to work.

### [AC-12] Contracts and queued work agree

- **Given** the implementation is ready for integration.
- **When** Living Spec and live proposal scopes are reconciled.
- **Then** repository responsibility and retired surfaces are stated, four earlier ADRs are superseded, and independent proposal outcomes remain valid.

## Screens

These drafts revise existing elements. Styling follows `docs/steering/visual-style.md`.
The user requested isolated UX review before UI implementation.

### Repository activity panel — `UX-sdd-proposals` / `UX-sdd-execution`

**Purpose**: start one explicit activity and open its PR Run. Facts to commit:
project/repository, selected unit and base, Planning/Development, effort/catalog.
Repository setup and workflow eligibility are the agent's responsibility. Secondary
history is below the start controls and never competes with the primary action.

**Content**: SDD unit (selected path/title and descriptive status); Native SDD
activity (intent selector, base and optional preferences, Start Planning/Start
Development); PR run (active/retained links); SDD batch (retired history disclosure
with exact IDs and PR/run links, no execution controls). Remove readiness/runtime
cards, executable milestone preview and phase/graph eligibility indicators.

**States**: populated offers start/open run; loading names the request in progress;
empty explains no selected unit and offers Browse repository; error keeps the
selected intent and offers retry of the exact request; retired history states why
it has no resume control. An unknown start result preserves request identity and
requires Check original request/Retry same request, rather than creating a new one.
Ownership-conflict names and links the active Run or retained claim. Reconciliation-
required explains that external work must be inspected and explicitly acknowledged
before another launch; retry alone cannot release it. The original repository,
unit/base/activity/preferences remain visible during an unknown publication result.
Competing starts are disabled until the exact request settles or its retained
owner is explicitly reconciled. Browsing another document does not erase that
recovery disclosure or create a replacement request.

**Interactions**:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select unit/activity/base | `UC-start-sdd-activity` 1 | populated | populated | | `CAP-SDD-native-delivery` | Exact intent shown |
| Start activity / Retry same request | `UC-start-sdd-activity` 2–4 | populated/error | loading | | `CAP-SDD-native-delivery` | Original request identity retained |
| Open run | `UC-start-sdd-activity` 5 | populated | populated | `UX-run-page` | `CAP-SDD-native-delivery` | Exact registered Run opens |
| Browse repository | global: leave execution context | empty/error/populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | Document browser opens |

### PR activity context panel — `UX-sdd-run`

**Purpose**: follow the PR Run, answer questions and inspect historical native
evidence. Facts to commit: Run/PR/head, current wait, selected answer and explicit
resume intent. Repository workflow reports are historical evidence, not live
eligibility or merge authority.

**Content**: PR run (state, unit/activity context and PR link); Run question
(existing question/answer/resume UI when open); Execution attempt (existing
request/reply history); Native SDD activity (retired evidence disclosure for old
snapshots only). Keep ordinary Run actions in their existing primary region;
remove native stage/gate/accept/reject/revise/revoke controls and runtime diagnostics.

**States**: populated follows the ordinary Run; waiting offers the question editor
and selected-answer resume; retired offers inspect-only history and explains
external work may still exist; loading/error offer the existing refresh/retry;
empty history states that no native evidence exists. Draft means waiting for the
operator's GitHub ready decision, not a failed repository check.

**Interactions**:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save answer | `UC-complete-sdd-workflow` 4 | waiting | waiting | | `CAP-PR-operator-decisions` | Answer saved; no implicit resume |
| Resume with selected answer | `UC-complete-sdd-workflow` 5 | waiting | populated | | `CAP-PR-operator-decisions` | Existing revision-checked request outcome |
| Open PR | `UC-complete-sdd-workflow` 6 | populated | populated | end | `CAP-PR-pull-request-delivery` | Exact GitHub PR opens |
| Inspect history / Refresh | global: inspect retained execution | retired/populated/error | retired/populated | | `CAP-SDD-native-delivery` | Read-only evidence or exact load error |

The target use-case flow replaces runtime admission with authorization/ref/owner
checks at start steps 2–4. Completion steps become: open Run (1), agent executes
repository work (2–3), answer if asked (4), explicitly resume (5), mark PR ready
in GitHub (6), observe CI/merge (7). Removed evaluator extensions are retired;
missing project/base, conflicting owner, uncertain publication and network errors
retain explicit failure/recovery outcomes.

Draft register updates: SDD unit → descriptive document and activity intent;
Native SDD activity → intent/Run context and retired evidence; SDD batch → retained
selection/outcome only. Run question and PR run representations/actions reuse
their current register rows.

Target interface mappings: completion step 1 opens `UX-run-page`; steps 2–3 show
existing request/reply progression in `UX-run-page`, with
`UX-sdd-run` supplying activity context; step 7 uses `UX-pipeline-runs` and
`UX-run-page` for CI/merge outcome. No removed readiness/stage panel serves these
steps. The existing project/ref/owner/publication error extensions stay on
`UX-sdd-proposals` with the recovery states above.
