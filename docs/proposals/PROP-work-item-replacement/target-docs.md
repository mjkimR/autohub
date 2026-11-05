---
id: PROP-work-item-replacement-target
title: Living Spec targets for PROP-work-item-replacement
summary: "Candidate contract and interface updates for link replacement work to original work items."
status: draft
proposal: PROP-work-item-replacement
created_at: 2026-11-05
targets:
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
  - file: docs/ux/work-plans/UX-work-plans.md
  - file: docs/steering/ux-objects.md
  - file: docs/architecture/ARCH-06-execution.md
---

# [Blueprint] PROP-work-item-replacement: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

`CAP-WORK-work-plan-execution` replaces rule 28 only for the explicit narrow
exception. Descriptive replacement completion still releases nothing. Rule 1
continues to reject cross-Plan Item graph edges. Rule 9 gains the scoped evidence
alternative; whole-Plan completion continues to require actual Item success.

Draft restatements (planned, not implemented):

- **Replacement evidence**: WHEN linking replacement work, Hub MUST preserve the
  original Work Item outcome, Work Plan lifecycle and PR run ownership.
- **Scoped satisfaction**: WHEN evaluating an existing local Item dependency,
  Hub MUST require ordinary predecessor success or a live acceptance of the
  exact replacement merge evidence described in the proposal.
- **Other admission fences**: WHEN a scoped acceptance exists, Hub MUST continue
  to enforce Plan dependencies, lifecycle, schedule, project and capacity gates.
- **Replacement lifecycle**: IF a relation forms a chain, reuses an endpoint or
  competes with a live link, THEN Hub MUST refuse it with 409.
- **Consumption**: WHEN admission uses acceptance, Hub MUST record consumption
  in the admission transaction.
- **Withdrawal**: IF an acceptance or its link is consumed, THEN Hub MUST refuse
  its withdrawal with 409.
- **Evidence identity**: WHEN acceptance is requested, Hub MUST validate exact
  project, connector/repository, target, Item specifications and confirmed merge.
- **Mutation history**: WHEN a replacement mutation commits, Hub MUST retain its
  request identity, actor, reason, revisions and immutable evidence events.

Planned enforcement: `REPL-01`–`REPL-07` plus the integration/migration/race checks
in the proposal. `CAP-PR-pull-request-delivery` is unchanged: acceptance consumes
existing merge evidence and creates no PR action.

## 2. Use Cases and Interface Plan

Extend `UC-execute-work-plan` after its prerequisite recovery extensions:

- **5d. Replacement work is required.** The operator selects an eligible stopped
  original and a distinct replacement Work Item, reviews their specifications
  and target, and confirms the link (`CAP-WORK-work-plan-execution`). Interface:
  `UX-work-plans` replacement disclosure. Linking ends without releasing work.
- **6c. Accept replacement evidence.** The operator reviews the merged replacement
  and selects one existing local dependent edge. Hub retains the decision and
  shows its remaining admission holds (`CAP-WORK-work-plan-execution`). Interface:
  `UX-work-plans` replacement disclosure. Resumes at step 3; original outcomes
  and whole-Plan dependency holds remain unchanged.
- **6d. Withdraw unconsumed evidence.** The operator selects an acceptance or
  link, reviews its scope, and withdraws it. Hub keeps history and rechecks
  eligibility; a consumed decision conflicts and shows the admitted dependent
  (`CAP-WORK-work-plan-execution`). Interface: `UX-work-plans` replacement
  disclosure. The withdrawal flow ends.
- **5e. Replacement is ineligible.** Hub shows the eligibility reason and leaves
  work held. The operator refreshes evidence or inspects the owning PR run;
  no automatic replacement or recovery occurs. Interface: `UX-work-plans`.
- ***b. Replacement write is stale or uncertain.** Stale state requires reload
  and another explicit review; transport uncertainty reuses the saved request
  identity to recover the result. Interface: `UX-work-plans` replacement disclosure.

Acceptance mapping: `REPL-01` covers 5d/6c; `REPL-02`, `REPL-03`, `REPL-07`
cover 5e; `REPL-04` covers 6d; `REPL-05` covers *b; `REPL-06` covers 6c holds.
Retain the original success guarantee; explicitly distinguish satisfied edge
from succeeded Work Item and completed Work Plan in the minimal guarantee.

## 3. Architecture and Decision Impact

`ARCH-06-execution` gains replacement evidence structure: evidence tables and
immutable consumption events MUST commit under project ownership with the
admission decision, retaining merge snapshots beyond detailed Run pruning.
Review the landed prerequisite Run/Item lock order before implementation.
Planned checks: PostgreSQL admission/withdrawal/recovery races; activity rollback;
migration and post-pruning integration cases. Until implemented, review only.
`PADR-work-item-replacement-evidence` records the decision and exact restatements.

## 4. Development Conventions and Governance

No governance/toolchain or operations changes. Regenerate the typed API client
with the accepted endpoints. Register the qualified terms “Work Item replacement
link” (explicit original/replacement relation, not execution ownership) and
“Work Item dependency acceptance” (operator decision for one edge, not Item
success or PR approval) in the existing glossary during reconciliation.

Extend the Work Item UX object row: replacement disclosure and compared
specifications; link replacement, inspect replacement evidence, accept for one
dependency, withdraw unconsumed acceptance/link, refresh status. PR run retains
inspect/control actions in its existing surface. Do not add a competing
representation for Execution attempt or Run question.

## 5. Before and After

Before: independently registered replacement work leaves all original dependencies
held. After: linking still leaves them held; explicit acceptance can satisfy one
existing Item dependency and shows why other holds remain. Original outcomes and
whole-Plan dependency behavior remain intact.

## 6. Screens

### Candidates

| Candidate | Primary region and task split | Trade-off |
| --- | --- | --- |
| Item disclosure inside `UX-work-plans` | Original evidence, replacement comparison and single-edge review within the selected Item | Chosen: preserves dependency context; history stays secondary |
| Dedicated replacement graph page | Cross-Plan visual graph and global decisions | More space but suggests broad substitution and adds navigation |

### Selected draft: `UX-work-plans` replacement disclosure

**Element:** panel extension in the existing Work Item row.
**Use cases:** `UC-execute-work-plan`. **Capabilities:** `CAP-WORK-work-plan-execution`.
**Purpose:** link replacement evidence and review one dependent edge. Facts to
commit are original failure, exact replacement, specification/acceptance texts,
repository/target, confirmed PR merge and affected dependent. The selected edge
is the primary region; historical events and PR details stay in secondary
paged disclosures. The existing Work Plan screen remains the entry and exit.

**Content tree:**

- Work Plan summary: lifecycle, revision, Plan dependency holds.
  - Original Work Item selected row: key/title, actual outcome, target and history.
    - Work Item replacement link review: original and replacement IDs/titles,
      full specification/acceptance expandable beside each other, repository and
      target, eligibility and reason field; shown while selecting a replacement.
    - Work Item dependency acceptance review: one explicitly selected dependent
      key/title and edge, original/replacement specification snapshots, PR URL,
      merge SHA/time, target and actor reason; shown only for merged evidence.
    - Work Item remaining holds: pause/revoke, schedule, other dependency,
      project or capacity; Plan completion disclaimer always visible.
    - Work Item replacement history: actor/reason/time, link/accept/withdraw,
      consumed dependent and retained merge links; shown on demand, paged.

**States:**

- `populated`: show current relation and accepted/consumed edges, or “Link
  replacement Work Item” if eligible. “Accept for dependency” is separate from
  linking. Refresh or close remains available.
- `empty`: no relation/history; show original evidence and link action if eligible.
- `loading`: keep the original context, show loading replacement candidates or
  history, offer close; disable mutations until evidence loads.
- `ineligible`: explain missing merge, wrong identity, active execution, unsupported
  outcome or retained chain. Offer refresh or inspect original/replacement PR run.
- `link-review`: require replacement selection and nonempty reason. Show both
  specifications/targets and “Link only; dependencies stay held”. Confirm/cancel.
- `accept-review`: no dependent selected by default. List existing local edges
  with one selectable row each; show selected dependent's other holds. Require
  reason and explicit coverage acknowledgement. “Accept for this dependency”
  confirms that original failure and Plan outcome stay unchanged and that after
  admission the decision cannot be withdrawn. Cancel returns without a mutation.
- `withdraw-review`: name exact link or acceptance, its affected edges and
  consumption status. Confirm explains future eligibility is removed; existing
  merges are retained. Consumed selection offers inspect admitted dependent
  instead of confirm.
- `busy`: disable competing submissions, retain reason and same request identity;
  show saving/checking status. Close returns to the Item with a pending indicator;
  reopening resumes lookup/replay of that same request.
- `accepted`: show the saved edge and remaining admission holds; show admitted
  progress or consumed state after refresh. No claim of immediate start/completion.
- `error`: preserve inputs and identity. Uncertain transport offers “Check saved
  request”; 409 shows exact conflict with reload/review action, no automatic retry;
  validation error identifies the field. Close remains available.

**Interactions:** proposed extension citations below will be added reciprocally
to `UC-execute-work-plan`; existing step 7 already covers history inspection.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open replacement disclosure | `UC-execute-work-plan` 5d, 6c | populated, empty | populated | | `CAP-WORK-work-plan-execution` | Original result, exact relation and available actions appear |
| Select replacement / enter reason | `UC-execute-work-plan` 5d | populated, empty | link-review | | `CAP-WORK-work-plan-execution` | Side-by-side specifications, target and link-only scope |
| Confirm link | `UC-execute-work-plan` 5d | link-review | busy | | `CAP-WORK-work-plan-execution` | Saved link returns populated; no edge releases; errors route to error |
| Select dependent / inspect evidence | `UC-execute-work-plan` 6c | populated | accept-review | | `CAP-WORK-work-plan-execution` | One exact edge, merge evidence and remaining holds shown |
| Confirm acceptance | `UC-execute-work-plan` 6c | accept-review | busy | | `CAP-WORK-work-plan-execution` | Saved result becomes accepted; errors preserve review inputs |
| Select withdrawal / confirm | `UC-execute-work-plan` 6d | populated, accepted | withdraw-review, busy | | `CAP-WORK-work-plan-execution` | Review precedes save; unconsumed withdrawal returns populated; consumed conflict shows dependent |
| Refresh / check saved request | `UC-execute-work-plan` *b, 6c | busy, error, accepted, ineligible | populated, accepted, error, ineligible | | `CAP-WORK-work-plan-execution` | Same request result or explicit holds/conflict; fresh revisions require another review |
| Inspect PR run | `UC-execute-work-plan` 5e | ineligible, populated | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | Owning PR run opens; replacement action does not control it |
| Inspect admitted dependent / history / next page | `UC-execute-work-plan` 6d, 7 | populated, accepted, withdraw-review | populated | | `CAP-WORK-work-plan-execution` | Dependent admission and immutable actor/reason history shown |
| Cancel review / close | `UC-execute-work-plan` 5d, 6c, 6d, *b | link-review, accept-review, withdraw-review, error, loading, busy, populated, accepted, ineligible, empty | populated | close | `CAP-WORK-work-plan-execution` | Returns to original Item; a pending save remains identified |

**Register check:** the drafted Work Item row above owns all replacement actions;
PR run inspection matches the existing root register. No new primary page,
notification surface or PR approval action is introduced.
