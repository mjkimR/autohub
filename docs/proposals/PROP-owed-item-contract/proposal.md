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
  and run → provider session (R19) have no path back.
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
- Backend layering stays `Router → UseCase → Service → Repository`; a cross-feature read composes through services,
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

Direction, to be settled in Planning:

- **Owed item model**: one row per owed exception, with the following fields. The field set is open (Q5).
  - `kind`: the exception class.
  - `cause`: why it waits, in operator terms.
  - `subject`: the object type, its ID and the project.
  - `primary_action`: one action the operator takes next.
  - `waiting_since`.
  - A stable `key` that is deep-link-ready.
- **Candidate kinds** (membership and Badge weight are Q1):
  1. Run questions and Native SDD activity requests: the existing actionable decision-inbox rows.
  2. Failed, paused and blocked PR runs, split into held by decision, held by operator and failed (Q2).
  3. Work Plans in `proposed` awaiting a decision.
  4. Work Item recovery and replacement or dependency acceptance.
  5. SDD batches in `attention`.
  6. Connection-test cleanup review.
  7. AI catalog holds that block queued work.
- **Read surface**: one authenticated read API returns the owed list (filterable by project and kind, cursor
  paginated), the total count, counts by kind and per-project counts. MCP exposure follows the decision list's
  precedent if Planning keeps it in scope. Each owning feature contributes its kind through its service layer.
- **One definition everywhere**: the shell Badge, the inbox or Attention worklist, the project strip, the dashboard
  Needs-you tile and notices count and route the same set. The second definition in `UX-dashboard` is removed or
  restated against the owed set.
- **Expected impact**:
  - A new or extended capability in `capabilities/delivery/` (or a new area if Planning chooses).
  - The reciprocal use cases (`UC-resolve-run-question`, `UC-receive-decision-notice` and the owning use cases of
    each kind).
  - UX deltas to `UX-app-shell`, `UX-decision-inbox` and `UX-dashboard`.
  - A glossary entry and a `ux-objects.md` register row.
  - Typed client regeneration (`just gen-ui-api`).
  - Possibly a migration if Q3 selects a persisted projection.

Non-goals:

1. A Thread or Desk concept that groups owed items into conversations or workspaces. The user deferred it.
2. Changing decision semantics: which Run questions or Native SDD requests are discovered or actionable, answer and
   resume rules, or the separate answer and resume records.
3. Changing the lifecycle or actions of Work Plans, Work Items, SDD batches, connection tests or AI catalogs. The owed
   item only reads and routes to existing actions.
4. Building the Phase 2 UI (Attention landing I2, project strip I3) or the run home (I1) in this proposal. Q9
   decides which consumer changes land with the contract.
5. The frontend-only `RepositoryView` `unit` parameter defect from the review. It is outside this backend contract.

Size: `L`. One feature spec can deliver the model, the read API and the migration of the shell count. If Planning
pulls in the run origin fields (Q6) or several UI consumers (Q9) as separate deliverables, the return sets
`needs_decompose`.

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

Evidence: `materials/owed-state-inventory.md` (scout round 1) and `envelopes/challenger-01.yaml`. Decisions marked
*open* wait for the user's answers to `envelopes/worker-01.yaml`.

- **Q2 (one item per root cause)**: a general suppression rule replaces the decision-versus-run case. Each root
  cause yields one owed item; the most specific actionable owner wins: decision > Work Item recovery or replacement >
  SDD batch attention > Work Item `attention` > run state. The others become context on that item. A run held by a
  decision appears only as the decision, with Answer as its primary action. A blocked run whose question was dismissed
  has no decision row and appears as a run item. The spec gives an acceptance example for each overlapping pair.
- **Q3 (read model)**: a query-time union over the owning tables, no persisted projection. Catalog-hold expiry and
  `waiting_since` are time-based, and a projection would add writes to five features' transactions. The decision kind
  reads the existing decision discovery projection. The cross-project predicates without an index today
  (`work_plans.state`, `sdd_batches.state`, `connection_tests.cleanup_status`) may gain partial indexes in Development
  if a measurement shows the need; the connection-test cleanup predicate needs a code-side adapter check, which the
  spec settles (filter the SQL candidates, then apply the adapter check to that bounded set).
- **Q4 (API shape and limits)**: one authenticated list read, filterable by project and kind, keyset-paginated by
  (`waiting_since`, `key`) with a page limit of at most 100, and a counts read (total, by kind, by project) that issues
  aggregates only, so the shell check stays one request at its current cadence. Acceptance criterion modeled on
  `SPEC-pending-decision-count` AC-04: one connection, one transaction, a fixed number of statements independent of
  row counts, no provider call, no session across external I/O. Paths and names follow the Q10 answer. MCP exposure is
  out of scope for this proposal.
- **Q5 (stable keys)**: `key` is `<kind>:<subject id>`; the decision kind embeds the existing `decision_key`
  unchanged, so notice links already sent still resolve. A resolved item leaves the set and its key is not reused for
  another subject; a cause change within the same kind and subject keeps the key.
- **Q6 (run fields)**: *open* (scope question). Recommended: only a per-run pending-decision flag stays here (it
  serves Q2 and the run rows' 100-row limit); run origin fields move to a sibling draft proposal.
- **Q7 (existing count)**: `actionable_total_count` on `DecisionPage` stays as is
  (`SPEC-pending-decision-count` Non-goal 5 allows a separate aggregate beside it). The owed count by kind for
  decisions equals `actionable_total_count` for the same visible scope; the spec states this as an acceptance criterion.
- **Q8 (notices)**: decision notices stay keyed on `decision_key` and fingerprint; no owed-item notices in this
  proposal. Run-stop notices stay a separate alert channel; the capability states that they are not the owed count.
- **Q1, Q9, Q10 and layering**: *open*, see the questions in `envelopes/worker-01.yaml`.
- **Boundaries**: `owns` now names the backend features, backend tests, the generated typed client, use cases and the
  other capability areas whose contracts gain an owed-kind rule (work-plans, sdd, connections, agents, notifications).
