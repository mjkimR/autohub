---
id: PROP-work-item-retry
title: Retry failed Work Items
summary: "Recover eligible failed Work Items while preserving successful work, prior execution evidence and external request identities."
status: accepted
created_at: 2026-11-05
target_area: capabilities/work-plans/
priority: high
size: L
planning_effort: high
dev_effort: high
milestone: MS-batch-recovery
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/work_plans/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/migrations/
    - modules/hub/tests/integration/migrations/
    - modules/hub/tests/integration/features/project_management/work_plans/
    - modules/hub/tests/unit/features/project_management/
    - modules/hub-ui/src/lib/features/project-management/work-plans/
    - docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    - docs/usecases/delivery/UC-deliver-pull-request.md
    - docs/decisions/
    - docs/capabilities/work-plans/
    - docs/usecases/work-plans/
    - docs/ux/work-plans/
    - docs/steering/
    - docs/architecture/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-work-item-retry] Retry failed Work Items

## 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` retains failed preparation and delivery outcomes but exposes no failed-Item retry API. Operators reconstruct work through another registration even when successful predecessors should remain untouched. A revision-checked recovery operation can let the original Work Plan finish while preserving its failed attempts.

### Source anchors

`modules/hub/app/features/project_management/work_plans/execution.py` records `preparation_failed`; `api.py` exposes Plan controls without an Item recovery command. `test_registration.py` covers replacement registration and preservation of the original outcome. These are inspected anchors, not a new test execution.

## 2. Technical Spike Questions

- **Q1**: Which preparation, failed, canceled and attention outcomes are eligible for recovery, and when is a new PR run required?
- **Q2**: How will prior linked runs and recovery attempts remain queryable without resetting attempt budgets or overwriting Item outcome evidence?
- **Q3**: How will an uncertain PR/comment effect be reconciled before recovery, and which revision, lease and capacity checks fence competing recovery requests?

## 3. Proposed Design & Impact

- Add an explicit Item recovery request with revision checks, authenticated actor, reason and idempotent request identity.
- Keep completed predecessor Items unchanged. Preserve prior execution links and identify each subsequent recovery attempt.
- Reconcile an existing owned branch/PR before preparing more work; retain unresolved external outcomes rather than treating them as permission to redispatch.
- Expose eligible recovery and refusal reasons on the existing Work Item surface. Reuse the PR execution owner for implementation, CI and merging.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: A three-Item chain fails at its second Item. Recovering that Item leaves the first Item's successful execution unchanged and releases the third only after confirmed success.
- **E2**: Replaying the same recovery request creates no second recovery attempt or external request; conflicting content under that identity is refused.
- **E3**: A stale revision or an uncertain external effect prevents a fresh dispatch and preserves the evidence needed for reconciliation.

### Non-goals

- **Scope Excluded**: Replacement dependency substitution, automatic retries of every failure, native SDD orchestration, rollback of remote effects and resetting exhausted execution budgets.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

Planning recommends the bounded recovery design below for `MS-batch-recovery`.
The milestone does not expand this feature scope. Direction acceptance and
Development remain separate Host decisions.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.

## 5. Planning decisions

### Options and recommendation

| Option | Benefit | Cost and risk | Decision |
| --- | --- | --- | --- |
| Retain Item and its PR run; typed durable recovery records | Existing request identities and attempt counters remain authoritative; old failure snapshots stay inspectable | Additive migration and a guarded PR-owner terminal recovery entry point | Recommended |
| Replace the linked PR run on every retry | Reuses ordinary enrollment | Resets per-run budgets and hides lineage unless another ledger is added; risks duplicate external work | Reject |
| Re-register a replacement Plan | Existing API requires no changes | Cannot satisfy the original dependencies and repeats successful work | Reject for this goal |

`PADR-work-item-recovery-lineage` records the durable design. Recovery is an
explicit operator request for unchanged work; specification, dependency and
target edits remain outside this command. No new PR run or automatic PR reopening
is introduced. This keeps the original Run budget and detailed history in place.

### Eligibility and routing

| Observed Item / external condition | Result |
| --- | --- |
| `preparation_failed`, no Run, no unresolved write | Accept recovery after exact-ref/ownership reconciliation; re-enter ordinary preparation admission with the same Item identity |
| Linked Run `failed` or `canceled`, same owned open PR, matching repository/target, prior delivery definitively stopped | Accept through a new guarded PR-owner recovery method on that same Run; retain every attempt, delivery and counter |
| Linked Run paused/blocked or running | Show existing Run controls; reject Item retry to avoid a competing owner |
| Uncertain preparation, comment/provider delivery, live lease or uncertain cancellation | Retain reconciliation hold and original request identities; no fresh dispatch |
| Same owned PR already merged correctly | Record confirmed success through ordinary observation; no request sent |
| Closed unmerged PR, missing Run, wrong-target merge, foreign branch/PR, native SDD project, exhausted automatic budget | Refuse retry with evidence and next action; no new Run, branch or budget reset |
| Successful Item, waiting Item, completed/revoked Plan | Refuse; no historical or successor mutation |
| Paused Plan | Refuse retry until explicit Plan resume; accepted recovery never silently activates a Plan |

A definitive preparation refusal can be retried after its underlying condition
is repaired. Existing owned branch work is reconciled; foreign work is never
overwritten. A closed PR can become eligible only after the operator separately
reopens it and Hub re-observes the original identity. Run failures whose cause
requires changing the work itself remain ineligible for this unchanged-work API.

### Request, transaction and dispatch contract

- Add `POST /{plan_id}/items/{item_id}/recover` and paged `GET /{plan_id}/items/{item_id}/recoveries` under the existing Work Plan API. Read responses include eligibility and a machine-readable refusal reason with human next action. Use existing project application access and authenticated actor; accept no caller-supplied actor.
- Require UUID `request_id`, `expected_revision` for the Plan, `expected_run_revision` when linked, and trimmed `reason` of 1–500 characters. Scope request uniqueness to the project; digest includes Item, actor and normalized command including observed revisions. Equivalent replay returns the original recovery record and current Item even after revisions advance; changed identity content returns 409. Scope/access checks precede replay, and replay precedes stale-revision rejection.
- Persist one typed recovery record with immutable command, prior Item/Run outcome, PR/branch/head identities, actor, reason and accepted revisions. Append immutable outcome events for reconciliation, admission, dispatch or refusal; do not overwrite the prior snapshot. Existing Run attempts remain distinct from this Work Item recovery history.
- Atomically record recovery, Plan activity and revision increment; rollback all on failure. A pending record gives one recovery owner per Item. Rejected preflight requests do not reserve dispatch capacity. Identical duplicate requests do not add activity or counters.
- Implement a documented shared lock protocol covering recovery, observation, ordinary controls, admission and retention. Preserve Run-before-Item locking when both are held; never acquire Project/Plan after holding Item in an inverse order. Determine the complete existing acquisition order during Development and use transaction phases if required. Every phase rechecks Plan/Run revisions, lease generation and recovery identity before applying remote observations.
- Commit reconciliation intent/lease before remote reads, release DB locks for I/O, then reacquire and validate. Expired workers cannot mutate the Item or Run. Unknown reads retain a pending record and are retried by the existing tick; a definitive refusal closes the record with no dispatch.
- Recovery passes existing schedule, dependency, enabled-project, catalog/quota and shared capacity gates. A recovered Run reserves exactly one slot using ordinary PR ownership. Run activation and durable delivery intent commit together; worker crashes and response loss reconcile that intent before another send. Reuse existing external request identities for uncertain delivery, and allocate a fresh execution request only after a confirmed stopped prior delivery and remaining owner budget.
- The guarded PR-owner entry point accepts only terminal Runs linked to this Item and recovery record. It refuses when another active Run owns the PR, rechecks ownership atomically during activation, and translates the active-owner uniqueness race to HTTP 409 with no dispatch from the losing request. A losing pre-acceptance transaction rolls back its intent; an already accepted reconciliation record closes as refused without activating its Run. It never increments `run.epoch` or resets epoch-scoped repair allowances. It preserves existing attempt numbers, fix/silent/delivery counters and prior request snapshots; it does not broaden ordinary Run resume. No manual budget override is part of Item recovery. A merged observation can finish without spending budget. Reuse the PR owner’s pushed-head/external-implementation reconciliation: when that evidence applies, continue current-head CI observation without another implementation delivery, retaining the epoch and prior attempts. Regression checks cover exhausted-current-epoch refusal with unchanged epoch, recovery racing ordinary enrollment with zero loser deliveries, and terminal recovery after implementation arrived with zero new delivery.
- Successful predecessor Items and their merge evidence remain untouched. Dependents release only on the recovered Item's confirmed original-target merge. Existing retention protects the linked unresolved Run; successful pruning retains the recovery snapshots and stable execution identity without requiring the detailed Run row.

### Migration and Development verification

Use additive recovery-record/event tables and indexes. Existing Items need no
invented historical attempts: show current legacy outcome as such. Preserve
existing registration IDs, branch markers and Run links. Verify migration upgrade
with existing failed and successful Items, uniqueness constraints and rollback.

Extend existing Work Plan integration tests and add PR-owner unit/integration
coverage under the declared boundaries. Required cases: three-Item chain and
unchanged predecessor; response-loss replay and conflicting payload; two distinct
requests racing; stale Plan/Run revision; pause/revoke racing each phase; expired
lease; unreadable remote outcome; lost PR/comment/provider response; capacity
contention; budgets unchanged/exhausted; terminal Run wrong target; correctly
merged reconciliation; closed PR refusal; activity failure rollback; legacy
migration and history after successful Run pruning. PostgreSQL must execute the
lock/race cases, not report SQLite skips as coverage. UI tests cover eligibility,
confirmation, preserved history and response-loss refresh. Regenerate API types
and run repository-required checks during Development.

No performance improvement is claimed; comparisons are invariant/count checks
against the same fixture with recovery disabled, not a second checkout.

### Assumptions and review offer

Conservative eligibility above is the recommended direction, not a separate
business question. Unsupported recovery remains a visible refusal rather than
implicit replacement. Development effort stays high because persisted history
and external request fencing change. Optional UX review is offered for the
Screens drafts in `PROP-work-item-retry-target` before code; the Host can include
it in the direction review. This turn neither accepts nor hands off the proposal.
