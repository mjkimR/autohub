---
id: SPEC-owed-item-contract
title: Owed item contract for operator debt
summary: Define one owed-item model and read surface so every exception class that waits for the operator reaches them through one count and one worklist with consistent definitions.
status: in-progress
created: 2026-11-13
related_capabilities:
  - CAP-PR-operator-decisions
  - CAP-PR-pull-request-delivery
  - CAP-WORK-work-plan-execution
  - CAP-SDD-workflow-control
  - CAP-CONN-connection-verification
  - CAP-AGENT-catalog-admission
  - CAP-NOTIFY-operator-notifications
related_usecases:
  - UC-resolve-run-question
  - UC-deliver-pull-request
  - UC-execute-work-plan
  - UC-execute-sdd-batch
  - UC-verify-project-connection
workflow: sdd-spec-feature
---

# [SPEC-owed-item-contract] Owed item contract for operator debt

## 1. Problem Statement & Motivation

Handed off from proposal PROP-owed-item-contract on 2026-11-13. Its accepted content, the user's Planning answers and
`ADR-owed-items-aggregate-read` are the authority for this spec.

- **Preserved Materials**: `docs/materials/2026-11/20261113-owed-item-contract`

Auto Hub succeeds through unattended throughput: agents deliver, and the operator steps in only on exceptions
("Exceptions first" in the product principles). The operator therefore needs one place that lists every exception
waiting for them, and one count that means the same thing on every surface.

Today operator debt has partial and conflicting definitions:

- The app shell Badge and `UX-decision-inbox` count only actionable decision-inbox rows (`UX-app-shell`,
  `CAP-PR-operator-decisions`, `actionable_total_count` from `SPEC-pending-decision-count`).
- The `UX-dashboard` Needs-you tile counts failed, paused and blocked PR runs.
- `docs/steering/visual-style.md` (Attention) defines operator debt as paused or blocked PR runs plus Run questions.
- Run-stop notices (`CAP-NOTIFY-operator-notifications`) announce paused, blocked and failed runs.
- Proposed Work Plans, Work Item recovery and replacement, Work Items in `attention`, SDD batches in `attention` and
  connection-test cleanup review wait for the operator but are visible only in their own per-project panels.
- No run field says that a run has a pending decision; run rows derive it from one 100-row decisions page.

Hypothesis: one owed-item model with one read surface makes every exception class reachable from any screen and
removes the conflicting definitions. The Phase 2 consumers (Attention landing, project exception strip) then read one
source within the shared database connection budget.

Constraints that bound the design:

- Auto Hub shares one PostgreSQL with another application: 20 connections, no pooler, a pool capped at 3 + 3. A
  request uses one connection at a time, holds no session across external I/O and nests no `AsyncTransaction`.
- Backend layering stays `Router → UseCase → Service → Repository`. The cross-feature read uses one read-only
  aggregate repository over owner models (`ADR-owed-items-aggregate-read`).
- Owed-item reads make no GitHub or other provider call, like the decision list (`SPEC-pending-decision-count` AC-04).

## 2. User Stories

- **US-1**: As an operator, I want one list of every exception waiting for me, across projects and object types, so
  that nothing owed stays hidden in a panel I did not open.
- **US-2**: As an operator, I want one owed count whose decision part equals the inbox count, so that every surface
  agrees on what waits for me.
- **US-3**: As a UI developer, I want a typed owed-item list, counts and a per-run pending-decision flag, so that the
  Phase 2 Attention landing and run rows need no client-side derivation.

The change extends the waiting states of `UC-resolve-run-question`, `UC-deliver-pull-request`,
`UC-execute-work-plan`, `UC-execute-sdd-batch` and `UC-verify-project-connection` with a shared owed-item read.

## 3. Non-Goals

1. **Scope Excluded**: a Thread or Desk concept that groups owed items into conversations or workspaces.
2. **Scope Excluded**: changing decision semantics: which Run questions or Native SDD requests are discovered or
   actionable, answer and resume rules, or the separate answer and resume records.
3. **Scope Excluded**: changing the lifecycle or actions of PR runs, Work Plans, Work Items, SDD batches, connection
   tests or AI catalogs, including a pause-actor field, a state-entry timestamp or an acknowledge action for failed
   runs. The owed item only reads and routes to existing actions.
4. **Scope Excluded**: any hub-ui screen change: the Phase 2 Attention landing and project strip, the shell Badge and
   Needs-you tile switch, and the run home. The shell keeps reading `actionable_total_count`.
5. **Scope Excluded**: the frontend-only `RepositoryView` `unit` parameter defect.
6. **Scope Excluded**: run origin fields on `PipelineRunRead` (`PROP-run-origin-links`).
7. **Scope Excluded**: owed-item notices; decision notices stay keyed on `decision_key` and fingerprint.
8. **Scope Excluded**: MCP exposure of owed items.
9. **Scope Excluded**: a persisted owed projection or a migration. Partial indexes are added only on a measured need.

## 4. Acceptance Criteria & Behavioral Contracts

The owed set has these kinds. A counted kind carries count weight; a quiet kind is listed without it.

| Kind | Counted | Waiting predicate | Primary action |
| --- | --- | --- | --- |
| `decision` | yes | An actionable decision-inbox row of a non-final run | `answer` |
| `stopped-run` | yes | A `paused` or `blocked` PR run not held by a decision | `resume-run` |
| `work-plan-proposed` | yes | A Work Plan in `proposed` | `review-plan` |
| `work-item-recovery` | yes | A Work Item recovery in `accepted` or `reconciling` | `inspect-recovery` |
| `work-item-replacement` | yes | An active replacement link whose original has a `waiting` dependent edge without a live acceptance | `accept-replacement` |
| `work-item-attention` | yes | A Work Item in `attention` | `inspect-work-item` |
| `sdd-batch-attention` | yes | An SDD batch in `attention` | `inspect-batch` |
| `connection-test-cleanup` | yes | A connection test whose cleanup the operator can review (`can_resolve`) | `review-cleanup` |
| `failed-run` | no | A `failed` PR run | `inspect-run` |

Root-cause suppression keeps one item per cause: decision > Work Item recovery or replacement > SDD batch attention >
Work Item `attention` > run state. A run is held by a decision when it has any decision-inbox row.

### [AC-01] Owed item shape and stable key
- **Given** one owed object of each kind in the table above
- **When** the operator reads `GET /api/v1/owed-items`
- **Then** the response is HTTP 200 and each item carries `key`, `kind`, `counted`, `cause`, `subject` (`type`, `id`,
  `project_id`), `primary_action` (`name`, `label`), `waiting_since` and `context` (`run_id`, `work_plan_id`,
  `work_item_id`, `sdd_batch_id`, `catalog_hold`)
- **And** every `key` equals `<kind>:<subject.id>`, the `decision` kind embedding the unchanged `decision_key`
- **And** a cause change within the same kind and subject (a paused run becoming blocked) keeps the key

### [AC-02] Decision items and their held runs
- **Given** a blocked run with an open Run question and a second run with an actionable Native SDD request
- **When** the operator reads the owed list and counts
- **Then** each actionable decision-inbox row appears once as a `decision` item with `primary_action.name` `answer`,
  and neither held run appears as a `stopped-run` item
- **And** the `decision` count equals `actionable_total_count` of `GET /api/v1/pipeline-runs/decisions` for the same
  scope, both unfiltered and filtered by `project_id`
- **And** after the question is dismissed, the decision item leaves the set and the still-blocked run appears as one
  `stopped-run` item

### [AC-03] Stopped runs and catalog-hold context
- **Given** a manually paused run, a blocked run without a decision row and a paused run whose AI catalog is
  quota-blocked with a future `available_at`
- **When** the operator reads the owed list
- **Then** each run appears as one counted `stopped-run` item with `primary_action.name` `resume-run`
- **And** only the run on the held catalog carries a non-null `context.catalog_hold` naming that catalog; the catalog
  itself is never an item

### [AC-04] Failed runs are quiet and recovery wins
- **Given** a failed run linked to a Work Item, and a failed run whose Work Item has a recovery in `accepted`
- **When** the operator reads the owed list and counts
- **Then** the first appears as a `failed-run` item with `counted` false and `context.work_item_id` set, and it adds
  nothing to `total`
- **And** the second appears only as a counted `work-item-recovery` item with `context.run_id` set
- **And** a recovery in `awaiting-admission` is not an item

### [AC-05] Work Plan and Work Item kinds
- **Given** a Work Plan in `proposed` and a Work Item in `attention` whose run is paused
- **When** the operator reads the owed list
- **Then** the plan appears as a counted `work-plan-proposed` item and the Work Item as a counted
  `work-item-attention` item with `context.run_id`, and the paused run does not appear as a `stopped-run` item
- **And** after the plan returns to `draft`, its item leaves the set

### [AC-06] Replacement acceptance
- **Given** an active replacement link whose original Item has a `waiting` dependent edge without a live acceptance
- **When** the operator reads the owed list
- **Then** one counted `work-item-replacement` item appears with `primary_action.name` `accept-replacement`
- **And** after that edge has a live acceptance, the item leaves the set

### [AC-07] SDD batch attention
- **Given** an SDD batch in `attention` whose claimed run is paused, and a second batch in `attention` whose claimed
  run has a decision-inbox row
- **When** the operator reads the owed list
- **Then** the first batch appears as one counted `sdd-batch-attention` item and its paused run does not appear
- **And** the second batch is suppressed into the run's `decision` item, whose `context.sdd_batch_id` names it

### [AC-08] Connection-test cleanup review
- **Given** a terminal connection test on an adapter with manual cleanup resolution and unconfirmed PR evidence, and a
  similar test whose cleanup is `completed`
- **When** the operator reads the owed list
- **Then** only the first appears, as a counted `connection-test-cleanup` item with `primary_action.name`
  `review-cleanup`

### [AC-09] Counts read
- **Given** the owed set of AC-01
- **When** the operator reads `GET /api/v1/owed-items/counts`, optionally with `project_id`
- **Then** the response is HTTP 200 with `total` (counted items only), `by_kind` (every kind, zero included, quiet
  kinds included) and `by_project` (counted items per project, projects with zero omitted)
- **And** `total` equals the sum of the counted kinds in `by_kind`, and a `project_id` filter restricts all three

### [AC-10] Filters, pagination and errors
- **Given** 105 owed items across kinds
- **When** the operator pages the list with `limit=100`
- **Then** the first page has 100 items, `has_more` true and a `next_cursor`, the second page has the remaining 5,
  the pages are disjoint and both are ordered by (`waiting_since`, `key`)
- **And** a `kind` or `project_id` filter returns only matching items
- **And** `limit=101` or `limit=0`, an unknown `kind`, a malformed cursor or a cursor reused with changed filters returns
  HTTP 422, an unknown `project_id` returns HTTP 404, and an unauthenticated request returns HTTP 401

### [AC-11] One connection, fixed statements, no provider call
- **Given** owed objects of every kind, measured once with one object per kind and once with three per kind
- **When** the operator reads the owed list and the counts
- **Then** each read runs in one transaction on one connection with the same number of SQL statements in both
  measurements (one statement without `project_id`, two with it)
- **And** neither read makes a provider call

### [AC-12] Per-run pending-decision flag
- **Given** a run with an open Run question and a run without decisions
- **When** the operator reads `GET /api/v1/pipeline-runs` and `GET /api/v1/pipeline-runs/{run_id}`
- **Then** `has_pending_decision` is true for the first and false for the second, independent of list paging
- **And** after the question is dismissed, later reads report false
- **And** a run loaded in a transaction reports the new value after a flush that adds or removes its decision rows, so
  run responses built after a mutation in that transaction need no extra statement

### [AC-13] Typed client and layering
- **Given** the merged backend
- **When** `just gen-ui-api` runs and then `just check-ui-api` and `uv run devkit rules check`
- **Then** the generated client exposes the owed-item list and counts and `has_pending_decision`, `check-ui-api`
  exits 0, and `RULE-app-router-repo-import` reports no violation for the owed-items router

## 5. Assumptions

- **Waiting time**: Hub records no state-entry time. `waiting_since` is the decision row's `waiting_since`, the
  recovery's `created_at`, the connection test's `finished_at` (falling back to `updated_at`) and otherwise the owner
  row's `updated_at`. Adding a state-entry column would change owner lifecycles (Non-goal 3).
- **Recovery that needs the operator**: the accepted predicate is a pending recovery except `awaiting-admission`, that
  is `accepted` or `reconciling`; `refused`, `running` and terminal recoveries are not items.
- **Replacement or dependency acceptance**: Hub stores no waiting flag (inventory). The derived predicate is an active
  link whose original Item has a dependent in `waiting` with no live (`active`) acceptance on that edge.
- **Connection-test adapter check**: the service evaluates the adapter registry in code to the set of adapters with
  manual cleanup resolution and passes it into the SQL predicate, so the bounded candidate filter and the keyset page
  stay one statement.
- **Batch suppression**: a batch whose claimed run has a decision row is suppressed into that decision, since the
  decision is the most specific actionable owner; the decision's `context.sdd_batch_id` keeps the link.
- **Scope**: the owed read has the visibility of the decision list: every authenticated user reads every project,
  optionally filtered by `project_id`.
