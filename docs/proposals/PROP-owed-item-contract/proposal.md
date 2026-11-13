---
id: PROP-owed-item-contract
title: Owed item contract for operator debt
summary: Define one owed-item model and read surface so every exception class that waits for the operator reaches them through one count and one worklist with consistent definitions.
status: reviewing                      # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: capabilities/delivery/
priority: high                        # critical | high | medium | low
size: L                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: medium               # low | medium | high (hint for Planning)
dev_effort: medium                    # low | medium | high (hint for Development)
boundaries:
  owns:
    - capabilities/
    - usecases/
    - ux/
    - steering/
    - modules/hub/app/features/
    - modules/hub/tests/
    - modules/hub-ui/src/lib/api/
  excludes:
    - docs/decisions/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-owed-item-contract] Owed item contract for operator debt

## 1. Background & Hypothesis

Auto Hub succeeds through unattended throughput: agents deliver, and the operator steps in only on exceptions
("Exceptions first" in the product principles). The operator therefore needs one place that lists every exception
waiting for them, and one count that means the same thing on every surface.

Today operator debt has two partial definitions and several invisible classes:

- The app shell Badge and `UX-decision-inbox` count only actionable decision-inbox rows: Run questions and Native SDD
  activity requests (`UX-app-shell`, `CAP-PR-operator-decisions`, `actionable_total_count` from
  `SPEC-pending-decision-count`). That spec's Non-Goal 5 deferred broader owed work to a later aggregate with its own
  field or endpoint.
- The `UX-dashboard` Needs-you tile counts failed, paused and blocked PR runs, a second definition. It shows no
  decision count and does not link to the inbox.
- `docs/steering/visual-style.md` (Attention) defines operator debt as paused or blocked PR runs plus Run questions awaiting a
  decision or a resume. Failed runs and the classes below are outside that definition.
- Run-stop notices (`CAP-NOTIFY-operator-notifications`) are a third definition: they announce paused, blocked and
  failed runs and in-flight runs that hold a `pause_reason`, keyed by run revision and linking the PR.
- These classes wait for the operator but reach no shared count or worklist:
  - Work Plans in `proposed` ("Needs a decision"; `CAP-WORK-work-plan-execution`).
  - Work Item recovery and replacement or dependency acceptance, and Work Items in `attention`.
  - SDD batch `attention` (`UX-sdd-batch`).
  - Connection-test cleanup review (`CAP-CONN-connection-verification`).
  - AI catalog holds that block queued work (`CAP-AGENT-catalog-admission`).

  Each is visible only inside its own panel. Work Plans are listed only per project
  (`/projects/{project_id}/work-plans`), and SDD batches only per project (`/projects/{project_id}/sdd/batches`), so a
  plan or batch in a project the operator does not open stays invisible.

The app-wide UX review of 2026-11-13 ranked this as its most consequential structural finding. The review covered the
OOUX framing of objects and relationships R1, R4, R9, R11 and R19 and three independent role passes. Its designer
increments I4 (an owed set across object types) and I5 (run origin links) both need backend data that the frontend
cannot derive:

- `PipelineRunRead` (`modules/hub/app/features/project_management/pipeline_runs/schemas.py`) carries no origin: no
  Work Item, Work Plan, SDD batch, provider session or enrollment source. Run → Work Item (R4), run → SDD batch (R11)
  and run → provider session (R19) have no path back. Planning moved these origin fields to `PROP-run-origin-links`.
- No run field says that the run has a pending decision. Run list rows derive it from one decisions page, so the
  answer is unknown beyond 100 rows.
- No endpoint lists Work Plans or SDD batch attention across projects.

The review's unconventional proposal names the shape: an owed item contract. Any object type raises one row with a
cause, a subject, one primary action and a deep-link-ready key. The shell Badge, landing or Attention page, inbox,
project strip and notices all count and route the same set.

Hypothesis: one owed-item model with one read surface will make every exception class reachable from any screen,
and will remove the conflicting definitions. The read surface returns a list, counts by kind and per-project counts.
It will also give the Phase 2 consumers (I2 Attention landing, I3 project exception strip) one source, within the
shared database connection budget.

Constraints that bound every option:

- Auto Hub shares one Aiven PostgreSQL with another application: 20 connections, no pooler, and Auto Hub's pool is
  capped at 3 + 3. A request uses one connection at a time. No session is held across external I/O. No
  `AsyncTransaction` is nested inside another.
- Backend layering stays `Router → UseCase → Service → Repository`. The cross-feature owed read uses one read-only
  aggregate repository over owner models (`PADR-owed-items-aggregate-read`); it was first drafted as composing
  through services,
  not through another feature's repositories.
- Owed-item reads make no GitHub or other provider call, like the decision list (`SPEC-pending-decision-count` AC-04).

## 2. Technical Spike Questions

- **Q1 (membership and weight)**: Which candidate kinds (§3) count toward the shell Badge, and which appear only as
  quieter items? Expected AI catalog holds and deliberate operator pauses are the boundary cases. Does a deliberate
  pause stay attention, as `visual-style.md` states today?
- **Q2 (run state distinction)**: How does the model separate a run held by a pending decision, a run held by the
  operator (pause) and a failed run? A held-by-decision run must not appear twice (as decision and as run), and its
  primary action is Answer, not Resume.
- **Q3 (read model)**: Is the owed set a query-time union over the owning tables, or a persisted projection like the
  decision discovery projection? Weigh freshness, index cost, migration and the one-connection rule. A union over six
  or more sources in one transaction must stay bounded.
- **Q4 (API shape and limits)**: What are the endpoint, the list ordering and the cursor pagination? Where do counts
  by kind and per-project counts live, and what are the page and count limits under the DB budget? Can the shell
  check remain one request at its current cadence?
- **Q5 (stable keys)**: What stable item key identifies an owed item across list, deep link and notice? Does it
  generalize the existing `decision_key`? What happens to a key when the item resolves or changes cause?
- **Q6 (run fields, I5)**: Should this proposal include a per-run pending-decision field and run origin fields
  (Work Item, Work Plan, SDD batch, provider session, enrollment source) on `PipelineRunRead`? Or should they split
  into a sibling proposal? The owed item needs a subject link, and the run home needs origin links.
- **Q7 (existing count)**: Is `actionable_total_count` on `DecisionPage` kept as is, superseded by the owed count,
  or aliased to the decision kind of the new count? Which count does the shell show while consumers migrate?
- **Q8 (notices)**: Should `CAP-NOTIFY-operator-notifications` decision notices target owed items generally? Which
  kinds notify, and does the notice deep link use the owed-item key?
- **Q9 (consumers and sequencing)**: Which UI consumers land with the contract? Candidates are the shell Badge, the
  inbox, the dashboard Needs-you tile, the Phase 2 I2 Attention landing and the I3 project strip. Which consumers
  follow in their own specs? Does Phase 2 wait for this contract or ship against the current decision count first?
- **Q10 (glossary)**: Which term names the concept for operators and in code: "owed item", "operator debt",
  "attention item" or "exception"? `docs/steering/glossary.md` has no entry, and `docs/steering/ux-objects.md`
  registers no such object.

## 3. Proposed Design & Impact

Direction settled in Planning (§5 records each decision):

- **Owed item model**: one row per root cause that waits for the operator, with these fields:
  - `key`: `<kind>:<subject id>`, stable and deep-link-ready; the decision kind embeds `decision_key` unchanged.
  - `kind`: the exception class.
  - `cause`: why it waits, in operator terms.
  - `subject`: the object type, its ID and the project.
  - `primary_action`: the one action the operator takes next, routed to the owner's existing action.
  - `waiting_since`.
  - `counted`: whether the item carries count weight (false for quiet items).
  - `context`: related objects suppressed into this item, and any catalog hold blocking its subject.
- **Counted kinds** (they make up the owed count):
  1. Actionable decision-inbox rows: Run questions and Native SDD activity requests.
  2. Paused or blocked PR runs not held by a decision, deliberate operator pauses included; a blocked run whose
     question was dismissed belongs here.
  3. Work Plans in `proposed`.
  4. Work Item recovery, replacement or dependency acceptance that needs the operator; recoveries in
     `awaiting-admission` are excluded.
  5. Work Items in `attention`.
  6. SDD batches in `attention`.
  7. Connection-test cleanup review.
- **Quiet items** (listed, no count weight): failed PR runs, linking to the Work Item recovery when one exists.
- **Context only** (never an item): AI catalog holds, shown on the run or batch they block.
- **Root-cause suppression**: the most specific actionable owner wins: decision > Work Item recovery or replacement >
  SDD batch attention > Work Item `attention` > run state. A run held by a decision appears only as the decision.
- **Read surface** under `/api/v1/owed-items`:
  - A list read filtered by project and kind, keyset-paginated by (`waiting_since`, `key`), page limit at most 100.
  - A counts read: owed total, counts by kind and by project, aggregates only.
  - Both run in one connection and one transaction with a fixed number of statements independent of row counts and no
    provider call, through one read-only aggregate repository (`PADR-owed-items-aggregate-read`).
  - The owed decision-kind count equals `actionable_total_count` for the same visible scope.
- **Per-run pending-decision flag**: `PipelineRunRead` gains a boolean saying the run has an actionable decision, so
  run rows no longer derive it from one 100-row decisions page.
- **Consumers**: this proposal ships the backend contract, its documents and the regenerated typed client. The shell
  keeps `actionable_total_count`. The Phase 2 Attention landing (I2) builds the all-kinds worklist and switches the
  shell Badge and the dashboard Needs-you tile to the owed count together, after this contract lands.
- **Naming**: the glossary and code term is "owed item" (API path `owed-items`); the operator-facing label is
  "Needs you".
- **Expected impact**:
  - A new owed-item capability in `capabilities/delivery/`, with each owning capability (work-plans, sdd,
    connections, agents) stating the predicate that makes its object owed.
  - `CAP-NOTIFY-operator-notifications` states that run-stop and decision notices are not the owed count.
  - Reciprocal use cases for the counted kinds' owners (`UC-resolve-run-question` and the owning use cases).
  - `UX-app-shell` and `UX-dashboard` record the owed count as the future source of the Badge and Needs-you tile,
    without a screen change here.
  - A glossary entry and a `docs/steering/ux-objects.md` register row; `docs/steering/visual-style.md` Attention
    restated against the owed set.
  - Typed client regeneration (`just gen-ui-api`). No migration, unless a measured need adds partial indexes.

Non-goals:

1. A Thread or Desk concept that groups owed items into conversations or workspaces. The user deferred it.
2. Changing decision semantics: which Run questions or Native SDD requests are discovered or actionable, answer and
   resume rules, or the separate answer and resume records.
3. Changing the lifecycle or actions of PR runs, Work Plans, Work Items, SDD batches, connection tests or AI catalogs,
   including a pause-actor field or an acknowledge action for failed runs. The owed item only reads and routes to
   existing actions.
4. Any hub-ui screen change: the Phase 2 UI (Attention landing I2, project strip I3), the shell Badge and Needs-you
   tile switch, and the run home (I1).
5. The frontend-only `RepositoryView` `unit` parameter defect from the review.
6. Run origin fields on `PipelineRunRead` (`PROP-run-origin-links`).
7. Owed-item notices; decision notices stay keyed on `decision_key` and fingerprint.
8. MCP exposure of owed items.

Size: `L`. One feature spec delivers the model, the read API, the per-run flag and the contracts.

## 4. Lifecycle & Retirement Criteria
<!--
- Preliminary decisions: devkit spec proposal padr owed-item-contract "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept owed-item-contract --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff owed-item-contract.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->

## 5. Planning Decisions

Evidence: `materials/owed-state-inventory.md` (scout round 1), `envelopes/challenger-01.yaml` and the user's answers
in `envelopes/answer-01.yaml`.

- **Q1 (membership, user)**: only operator-actionable kinds are counted (§3). Failed runs are quiet items without
  count weight because no in-scope action clears them; catalog holds and `awaiting-admission` recoveries are system
  holds that clear by themselves, so catalog holds are context only and those recoveries are excluded.
- **Q1 (deliberate pauses, user)**: every paused or blocked run not held by a decision counts, as
  `docs/steering/visual-style.md` states; no pause-actor field.
- **Q2 (one item per root cause)**: the suppression order in §3; the spec gives an acceptance example for each
  overlapping pair (decision and run, recovery and failed run, batch attention and owner run and native decision, Work
  Item `attention` and run).
- **Q3 (read model)**: a query-time union over the owning tables, no persisted projection; catalog-hold expiry and
  `waiting_since` are time-based. The decision kind reads the existing decision discovery projection. Partial indexes
  on `work_plans.state`, `sdd_batches.state` or `connection_tests.cleanup_status` are added only on a measured need.
  The connection-test cleanup predicate filters SQL candidates, then applies the adapter check to that bounded set.
- **Q4 (API shape and limits)**: §3 read surface, with an acceptance criterion modeled on
  `SPEC-pending-decision-count` AC-04. MCP is out of scope.
- **Q5 (stable keys)**: `<kind>:<subject id>`, the decision kind embedding `decision_key`. A resolved item leaves the
  set and its key is not reused; a cause change within the same kind and subject keeps the key.
- **Q6 (run fields, user)**: only the per-run pending-decision flag stays; origin fields moved to the draft
  `PROP-run-origin-links`.
- **Q7 (existing count)**: `actionable_total_count` stays as is (`SPEC-pending-decision-count` Non-goal 5) and the
  shell keeps reading it; the owed decision-kind count equals it.
- **Q8 (notices, user)**: owed-item notices deferred; run-stop notices stay a separate alert channel.
- **Q9 (consumers and sequencing, user)**: backend contract, documents and typed client only; the Phase 2 Attention
  landing switches the Badge and Needs-you tile together after this contract lands. Phase 2a navigation regroup and
  project workspace work proceed independently.
- **Q10 (naming, user)**: "owed item" in glossary, code and API path; label "Needs you".
- **Layering (user)**: one read-only aggregate repository (`PADR-owed-items-aggregate-read`).
- **Boundaries**: `owns` names the backend features and tests, the generated typed client, use cases, capabilities,
  UX documents and steering; no hub-ui screen path.
