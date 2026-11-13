---
id: SPEC-pending-decision-count
title: Exact pending-decision count
summary: Expose an exact count of actionable pending decisions on the decision list and show it unbounded in the app shell signal.
status: planned
created: 2026-11-13
related_capabilities:
  - CAP-PR-operator-decisions
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-pending-decision-count] Exact pending-decision count

## 1. Problem Statement & Motivation

The authenticated navigation panel (`UX-app-shell`) signals operator-owed decisions from any screen. It derives
the count from one page of `GET /api/v1/pipeline-runs/decisions` (first 50 rows) by counting rows with
`actionable=true`. With more rows than the sample, it can only show a lower bound ("50+"), and a sample with no
actionable row but more rows behind it is undecidable and stays neutral even when decisions are owed further down
the worklist. Operators therefore see an imprecise or missing signal exactly when the backlog is largest.

The backend already holds the persisted discovery projection that defines the inbox rows, so it can count the owed
rows exactly in one query. The count definition stays the one `UX-decision-inbox` uses for its attention rows:
actionable "Needs decision" and "Answer saved — resume pending" rows; "Answer publication pending" rows
(`actionable=false`) are not owed.

## 2. User Stories

- **US-1**: As an operator, I want the shell to show the exact number of decisions I owe across visible projects,
  so that I can judge the backlog from any screen without opening the inbox.
- **US-2**: As an API or MCP client of the decision list, I want the number of actionable rows matching my filters
  independent of pagination, so that I need not page through the whole worklist to size it.

## 3. Non-Goals

1. **Scope Excluded**: a separate count endpoint, MCP tool or push/streaming update; the shell keeps its existing
   polling cadence and single request per check.
2. **Scope Excluded**: showing the count inside `UX-decision-inbox` or changing its rows, filters, ordering or
   pagination.
3. **Scope Excluded**: changing which rows are discovered or actionable, the discovery projection, its indexes or any
   migration.
4. **Scope Excluded**: per-project or per-kind counts in the shell; the shell signal stays global and unfiltered.

## 4. Acceptance Criteria & Behavioral Contracts

The count field is `actionable_total_count` on the existing `DecisionPage` response (decided in
`PLAN-pending-decision-count`).

### [AC-01] Exact count beyond the page
- **Given** 105 open run questions on one nonterminal Run in the discovery projection
- **When** an authenticated operator requests `GET /api/v1/pipeline-runs/decisions?limit=1`
- **Then** the response is 200 with one item, `has_more` true and `actionable_total_count` 105
- **And** the next page requested with the returned cursor reports the same `actionable_total_count` 105

### [AC-02] Only actionable rows are counted
- **Given** a native decision row whose answer publication is pending (`actionable=false`) and no other row
- **When** the decision list is requested
- **Then** the response lists that row and reports `actionable_total_count` 0
- **And** after an ordinary Run question is answered but not resumed ("Answer saved — resume pending"), that row is
  counted (`actionable_total_count` 1), and after the question is dismissed the list is empty with
  `actionable_total_count` 0

### [AC-03] The count follows the list filters
- **Given** actionable rows in the projection
- **When** the list is requested with `project_id`, `kind` or `question_state`
- **Then** `actionable_total_count` counts only actionable rows that the same filters admit on nonterminal Runs,
  ignoring `cursor` and `limit`
- **And** a filter that admits no row returns `items` empty and `actionable_total_count` 0; an unknown `project_id`
  still returns 404 and a malformed cursor still returns 422

### [AC-04] One connection, one count query, no provider call
- **Given** a decision list request
- **When** it is served
- **Then** the page rows and the count are read inside one database transaction on one connection, the count is one
  aggregate statement, and no GitHub or other provider call is made

### [AC-05] Shell shows the exact count
- **Given** the decision list reports `actionable_total_count` N > 0
- **When** the app shell checks pending decisions
- **Then** it requests the list with `limit=1` and no filters, shows "N" (never "N+") on the Decisions Badge and the
  narrow-header "N pending" Badge, and announces "N pending decisions" ("1 pending decision" for one)

### [AC-06] Neutral states
- **Given** the count is 0, the check is loading, or the request fails or returns no data
- **When** the shell renders
- **Then** it shows no attention rule and no count Badge

### [AC-07] Typed client is current
- **Given** the backend schema adds `actionable_total_count`
- **When** `just check-ui-api` runs after `just gen-ui-api`
- **Then** it passes and the generated `DecisionPage` declares `actionable_total_count: number` as required

## 5. Screens

### UX-app-shell: Pending-decision signal (delta)

- Source: one read of the Decision inbox list (`GET /api/v1/pipeline-runs/decisions`, all visible projects, no
  filters, `limit=1`) at the existing cadence; the shell uses its `actionable_total_count` and ignores the item.
- Count: exact; the "N+" lower bound and its "N or more pending decisions" phrase are removed, and so is the
  undecidable-sample state.
- States: `decisions-owed` when the count is above zero; `decisions-neutral` when it is zero, loading or failed.
- Layout, emphasis, Badges, rule and interactions are unchanged.

## 6. Assumptions

- The count reuses the list's filter and visibility semantics (nonterminal Run joined with an existing Project);
  the shell already treats every `actionable` row as an attention row, so its definition does not change.
- The optional `ux-reviewer` round is not run: the screen delta removes a "+" suffix and one neutral state without
  changing layout, emphasis or interactions.
- The page rows and the count are separate statements in one transaction; under read-committed isolation a
  concurrent owner change between them may make the count differ from the rows by that change until the next check.
