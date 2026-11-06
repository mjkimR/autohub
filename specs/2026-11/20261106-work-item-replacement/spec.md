---
id: SPEC-work-item-replacement
title: Link replacement work to original Work Items
summary: Record explicit replacement relationships and dependency satisfaction decisions without rewriting original Work Plan outcomes.
status: planned
created: 2026-11-06
depends_on:
  - SPEC-work-item-retry
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-work-item-replacement] Link replacement work to original Work Items

## 1. Problem Statement & Motivation

Handed off from proposal PROP-work-item-replacement on 2026-11-06.
- **Preserved Materials**: `docs/materials/2026-11/20261106-work-item-replacement`
- Target Docs Blueprint: `PROP-work-item-replacement-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` supports replacement registrations through descriptive links and optional branch attachment. It has no structured replacement relationship, and replacement completion does not satisfy the original dependencies. Explicit operator-selected replacement evidence can remove manual graph reconstruction without falsifying the original outcome.

#### Source anchors

`modules/hub/tests/integration/features/project_management/work_plans/test_registration.py::test_replacement_keeps_canceled_evidence_and_does_not_release_old_dependents` enforces the existing boundary. This is a feature proposal to extend that contract, not a claim that the existing behavior is defective.

## 2. User Stories

- **US-1**: As a developer/agent, I want to implement Link replacement work to original Work Items so that system capabilities are extended.

## 3. Non-Goals

1. **Scope Excluded**: automatic semantic equivalence, replacement chains, whole-Plan satisfaction, PR mutation and rewriting original outcomes.
2. **Scope Excluded**: deployment, monitoring, SDK execution and general cross-Plan Item dependency graphs.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Scoped release
- **Given** stopped original A with waiting B/C and linked replacement R.
- **When** R succeeds and its evidence is explicitly accepted for B→A.
- **Then** only that existing edge becomes satisfied; linking and merge alone release nothing.

### [AC-02] Exact evidence
- **Given** replacement identities or merge evidence differ.
- **When** link or acceptance is requested.
- **Then** 404/409 preserves outcomes, ownership and all holds.

### [AC-03] Retained roles
- **Given** retained A→R relation exists.
- **When** a chain, role switch or replacement reuse is requested.
- **Then** 409 preserves history; unconsumed withdrawal permits A→distinct R2 only.

### [AC-04] Atomic consumption
- **Given** live acceptance exists.
- **When** withdrawal and admission race.
- **Then** project serialization determines eligibility; admitted consumption and preparing commit atomically, consumed withdrawal returns409.

### [AC-05] Replay
- **Given** an operation response was lost.
- **When** same request and actor replay or changed input arrives.
- **Then** identical replay returns original result plus current evidence, changed payload/actor returns409 without duplicate events.

### [AC-06] Remaining holds
- **Given** accepted edge exists.
- **When** plan lifecycle, Plan dependencies, schedule, capacity or another Item edge blocks.
- **Then** no admission occurs and original Item/Plan outcomes remain unchanged.

### [AC-07] Retention
- **Given** replacement confirmed merge remains after detailed Run pruning.
- **When** acceptance is requested.
- **Then** retained exact merge snapshot supports acceptance without provider calls or PR mutation.

### [AC-08] Review and edits
- **Given** a live link or unresolved request exists.
- **When** specification edit or UI mutation is attempted.
- **Then** linked endpoint edits are refused; UI binds displayed revisions/digests/merge, preserves immutable retry on uncertainty and refreshes conflict for explicit review.

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Technical Spike Findings

The inspected scheduler gates local Item edges by `succeeded`, and Plan edges by
`completed`. Its project lock serializes registration/control/admission. The
replacement registration regression confirms that another Plan's merge does not
release original dependencies. `PROP-work-item-replacement-target` defines the
narrow exception; all other release conditions remain in force.

#### Alternatives

| Option | Benefit | Cost / risk | Recommendation |
| --- | --- | --- | --- |
| Typed replacement link and per-existing-Item-edge satisfaction | Durable evidence and exact release scope; preserves outcomes | Additive schema and explicit reviews | Choose |
| Descriptive links and manual recreation of dependent work | Existing behavior, no schema | Cannot release existing dependencies or preserve their admission identity | Retain as fallback for unsupported cases |
| General cross-Plan Item dependencies or successor substitution | Broad automation | New graph semantics, cycles and implicit equivalence | Excluded |

### 3. Proposed Design & Impact

#### Planning decisions

- Keep original Work Item outcome, original Work Plan lifecycle, registration
  identity, recovery history and PR run ownership intact. Replacement is a
  distinct Work Item in another Work Plan, with its own registration and PR run.
- Use an append-only replacement link and a separate acceptance for exactly one
  existing local Item dependency `(dependent_item_id, original_item_id)`.
  Linking alone changes no eligibility. No whole-Plan dependency can be accepted
  through this action; a revoked or unsuccessful Plan remains blocking for its
  Plan dependents. This narrower boundary is the recommended direction.
- Permit several historical candidate links but one active link per original
  Work Item and one live acceptance per dependency edge. A replacement cannot
  replace multiple originals. An Item cannot be both original and replacement
  in any retained link, including withdrawn links. After an unconsumed link is
  withdrawn, its original may link a distinct, previously unlinked replacement.
  A replacement endpoint is lifetime-bound to its original; it cannot be reused
  in another link. Endpoint roles cannot switch. No chains are followed.
- Eligible originals are stopped unsuccessful Work Items: `preparation_failed`,
  `failed`, `canceled` or `revoked`, with no active preparation/recovery lease or
  nonterminal linked PR run. `attention`, `blocked`, `paused`, unknown remote
  effects and merely waiting work remain ineligible. Prior confirmed success
  is ineligible. Revalidate this state vocabulary against the landed retry spec.
- Accept only a replacement's own retained confirmed merge evidence from the
  same project, connector/repository binding and original target branch. It must
  contain PR number/URL, merge SHA, stable execution identity and completion time.
  A link may be made before replacement success; acceptance waits for success.
  Operator review supplies the claim that its specification covers the original;
  Hub verifies identity and merge facts, not semantic equivalence.
- The replacement's PR run never moves to the original and this feature never
  dispatches, reopens, resumes or merges a PR. Existing PR policy and original
  outcome controls remain authoritative. Successful original recovery takes
  precedence as ordinary evidence; historical replacement acceptance remains
  visible and cannot rewrite that recovery.

#### Identity, mutation and concurrency

Add typed link, acceptance and event records. A link stores exact original and
replacement IDs, Plan revisions, specification digests, repository/connector and
target snapshots, actor, reason and request identity. An acceptance adds the exact
existing edge, accepted merge snapshot, authenticated actor, reason, timestamp
and monotonic evidence revision. Events retain link/accept/withdraw decisions;
activity saving and the evidence mutation commit or roll back together.

Provisional HTTP shape under the existing project Work Plan API: POST
`/{plan_id}/items/{item_id}/replacement-links`, GET the same collection, POST
`/{plan_id}/items/{item_id}/replacement-links/{link_id}/acceptances` and POST
`/{plan_id}/items/{item_id}/replacement-links/{link_id}/withdraw`. The original
Plan owns the URL. Acceptance names one dependent Work Item; no arbitrary edge
creation is accepted. GET includes both endpoints, edge decisions, revisions and
consumption history. Responses use existing application authorization; body actor
fields are refused. Strict schemas reject unknown fields.

Each POST requires `request_id`, nonempty reason, expected original/replacement
Plan revisions and expected evidence revision. Acceptance also binds displayed
Item specification digests and replacement merge identity. Idempotency is scoped
to project and operation; an identical normalized request by the same actor
returns its retained result even after consumption/withdrawal, while changed
payload or actor under that identity returns 409. Replay is checked before current
revision eligibility. The authoritative read returns the original operation's
result together with current evidence state. An unknown response keeps the same
request ID; it does not invite a fresh command.

Mutations take the existing project lock before deterministic Plan/Item/evidence
locks. They recheck project binding, lifecycle, revisions, eligibility and edge
existence under those locks. Evidence mutation increments original Plan and
evidence revisions; replacement Plan revisions are checked, not incremented.
Original/replacement draft edits that change specification/target or remove an
endpoint are refused while a live link exists. Withdraw first where allowed.
Terminal originals therefore remain inspectable without reviving their Plan.
The new locks preserve the prerequisite's established Run-before-Item order;
Development must derive a compatible order from the landed retry implementation
rather than acquiring a Run after an Item lock.

Dependency evaluation accepts either ordinary predecessor success or a live
accepted record for that exact edge whose immutable evidence matches the locked
identity. It never follows relation chains. All Plan dependencies, schedule,
capacity, enablement, pause/revoke and normal admission fences still apply.
Admission records an immutable consumption event containing the acceptance ID
in the same transaction that sets `preparing`. Once any acceptance on a link is
consumed, withdrawing the link or that acceptance returns 409. Withdrawal before
consumption appends an event and removes future eligibility; it does not undo a
merge. Withdraw an individual unconsumed acceptance through the same operation
with its acceptance ID, or the entire link with no acceptance ID. A withdrawn
acceptance can be accepted again on the same still-active link using a fresh
request/revision. Link withdrawal is permanent for that pair; the original may
select a distinct previously unlinked replacement after an unconsumed link is
withdrawn. Concurrent withdrawal/admission,
competing acceptance, recovery and pause/revoke serialize on project ownership;
exactly the winning committed action determines eligibility. No downstream work
is canceled or rewound by this feature.

Use 404 for inaccessible/missing project-scoped objects, 422 for malformed input,
and 409 for stale revision, ineligible identity/state, chain, live competition,
missing original edge or consumed withdrawal. API detail must identify the
conflict reason and current evidence revision. The UI refreshes for review after
409; it never automatically retries with fresh revisions. Reuse the project's
existing error envelope rather than introducing a global error framework.

#### Persistence and verification

Use additive tables, composite project/Item ownership constraints, unique request
identity/digest, a unique active-original link, unique active replacement owner,
and unique live acceptance per edge. Retained history prevents endpoint role
changes and replacement reuse; an original can have historical withdrawn
candidates and one live candidate. Existing rows receive no synthetic
links/acceptances.
Endpoints, acceptance snapshots and consumption events survive detailed Run
pruning; unresolved original Runs keep existing retention protection. Normal
Work Plan retention does not delete the evidence. No retention worker expansion
is required: store snapshots before acceptance and reference Plan/Item lifetime.

Development checks include PostgreSQL races for acceptance/withdrawal/admission,
competing links, pause/revoke and original recovery; transactional activity
failure; request replay after response loss and changed payload/actor; exact
wrong project/repository/connector/target/merge refusal; chains and reverse
cycles; two dependents with only one accepted edge; all remaining dependencies,
schedule and capacity holds; consumed withdrawal; migration of legacy rows;
pruned replacement Run with retained evidence; and original/Plan outcomes
unchanged. Preserve the existing descriptive replacement regression unchanged
when no acceptance exists. UI coverage walks link, evidence review, accept,
withdraw, conflict and response-loss recovery. Regenerate typed API resources.
Run `just lint`, `just check`, affected backend/UI tests and PostgreSQL race tests
after implementation. Planning executed no product tests and claims no timing
improvement. Invariant comparisons use the same fixture with acceptance absent,
without checking out another head.

#### Acceptance examples

- **REPL-01**: Given stopped original A and waiting local dependents B/C, when
  replacement R is linked and merges, then B/C remain held until an operator
  accepts R for B's A edge; only that edge becomes satisfied.
- **REPL-02**: Given replacement evidence for another target or project, when
  acceptance is requested, then 409/404 leaves all original outcomes and holds.
- **REPL-03**: Given A has a retained replacement relation, when A or its
  replacement is used in a chain/reverse cycle, then 409 retains history.
- **REPL-04**: Given accepted but unconsumed evidence, when withdrawal wins before
  admission, then no dependent starts; when admission wins, withdrawal conflicts
  and retained consumption explains why.
- **REPL-04b**: Given an unconsumed A-to-R1 link is withdrawn, when A links
  distinct unlinked R2, then the new link is accepted with history retained; R1
  cannot serve another original and A/R1 cannot switch roles.
- **REPL-05**: Given a response-lost accepted request, when identical replay and
  conflicting replay arrive, then the first returns its saved result and the
  second conflicts without duplicate events.
- **REPL-06**: Given an accepted edge on a paused/revoked original Plan or a
  dependent still held by schedule/capacity/another edge, when ticking, then it
  stays unadmitted; no original Item becomes succeeded or Plan completed from
  replacement acceptance, and Plan dependents remain held.
- **REPL-07**: Given replacement success has retained merge evidence after Run
  pruning, when accepted, then the evidence snapshot suffices; missing or
  ambiguous evidence is refused and no PR action is issued.

#### Non-goals

- **Scope Excluded**: Automatic semantic equivalence, automatic successor
  substitution, general cross-Plan Item scheduling edges, whole-Plan dependency
  satisfaction, replacement chains, rewriting original outcomes and PR authority.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection, CI trigger changes and successful-work replay.

### 4. Lifecycle & Retirement Criteria

#### Planning-only prerequisite override

User authority starts this HIGH-effort Planning turn before
`SPEC-work-item-retry` Development completes. This changes sequencing for
Planning only. The original proposal of this spec and the decision now recorded
as `ADR-work-item-recovery-lineage` were provisional API/history foundations at base
`448247462d8d54d227eae7e68a70c762de12d46a`; no dirty concurrent implementation
was consulted. It is not a completed SPEC dependency.

Before handoff or implementation, the Host must replace the prerequisite edge
with its exact completed spec anchor through the normal reference process and
revalidate state vocabulary, recovery exclusion, locks, snapshot retention,
request identity, activity and API shapes against the landed prerequisite. If
it changes the direction above, return to Planning and rerun affected reviews.
This run does not authorize plan-accept, handoff or implementation. The Host
presents the reviewed source and exact effects at the ordinary gates.

The proposal remains reviewing. `PROP-work-item-replacement-target` carries the
affected contracts and stable Screens drafts. No user-only design question is
assumed: routine conservative choices above remain recommendations for direction
review. Completion requires verified implementation and reconciliation.


## 6. Implementation assumptions

`SPEC-work-item-retry` is completed. `WorkPlanService.control` sets unstarted Items to `revoked`, so the accepted vocabulary remains valid. Replacement supports stopped originals on terminal Plans while retry retains its separate active-Plan requirement. Locks use Project, deterministic Plans, Runs, Items, then evidence. The accepted narrow relation direction in `ADR-work-item-replacement-evidence` is retained.
