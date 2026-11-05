---
id: SPEC-work-item-retry
title: Retry failed Work Items
summary: "Recover eligible failed Work Items while preserving successful work, prior execution evidence and external request identities."
status: in-progress
created: 2026-11-05
related_capabilities: [CAP-WORK-work-plan-execution, CAP-PR-pull-request-delivery]
related_usecases: [UC-execute-work-plan, UC-deliver-pull-request]
workflow: sdd-spec-feature
---

# [SPEC-work-item-retry] Retry failed Work Items

## 1. Problem Statement & Motivation

Eligible failed work needs to finish in its original dependency graph. `CAP-WORK-work-plan-execution` currently requires replacement registration; `CAP-PR-pull-request-delivery` remains the sole delivery and merge owner.

## 2. User Stories

- As an operator, recover unchanged failed work without repeating successful predecessors in `UC-execute-work-plan`.
- As an operator, inspect recovery history and resolve uncertain delivery without duplicating requests in `UC-deliver-pull-request`.

## 3. Non-Goals

- **Scope Excluded**: replacement dependency substitution, automatic retries of every failure, native SDD orchestration, remote rollback, automatic PR reopening, budget resets, changed specifications, operational rollout and CI trigger changes.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Retain the dependency chain

- **Given** an active three-Item Plan with a successful predecessor and a preparation_failed second Item.
- **When** the operator repairs the cause and recovers the second Item.
- **Then** the same second Item returns through ordinary admission; the first Item and merge evidence stay unchanged, and the third starts only after the second merges into the original target.

### [AC-02] Retain terminal Run lineage

- **Given** a failed or canceled linked Run on the same owned open PR with definitive stopped delivery and remaining budget.
- **When** recovery is admitted.
- **Then** the original Item and Run remain linked, epoch and all prior attempts/deliveries/counters remain unchanged, and activation and a new durable intent commit together.

### [AC-03] Idempotent authenticated request

- **Given** a project-accessible recovery command with UUID request_id, Plan revision, linked Run revision and trimmed reason of 1–500 characters.
- **When** its equivalent command is replayed after revisions advance.
- **Then** the original recovery record and current Item return with no extra activity, event, capacity reservation or external request; changed Item, actor or command under the same project-scoped identity returns HTTP 409.

### [AC-04] Revision and lifecycle fencing

- **Given** stale Plan/Run revisions, paused/revoked/completed Plans or an unexpired Item/Run lease.
- **When** an operator requests recovery.
- **Then** HTTP 409 prevents acceptance or dispatch and retains prior evidence; paused Plans require explicit resume.

### [AC-05] Refuse unsupported recovery

- **Given** a successful/waiting Item, active/paused/blocked Run, missing/foreign/wrong-target/closed-unmerged PR, native sdd project or exhausted budget.
- **When** recovery is requested or reconciliation establishes that condition.
- **Then** recovery is refused with machine-readable reason and supported next action; no replacement Run, branch, PR reopen, epoch increment or budget reset occurs.

### [AC-06] Reconcile uncertainty

- **Given** a committed recovery intent encounters unknown PR or prior delivery/comment/provider outcome.
- **When** the worker cannot definitively reconcile it.
- **Then** the record stays reconciling with its original identity, no fresh request is sent, and an existing tick retries after its lease expires.

### [AC-07] Atomic history and activity

- **Given** a valid recovery command and any failure saving its history or Plan activity.
- **When** the transaction commits or rolls back.
- **Then** one immutable prior-outcome snapshot, actor, reason, accepted revisions, PR/branch/head identities and append-only events accompany one Plan revision increment; persistence failure rolls all of them back.

### [AC-08] Shared admission gates

- **Given** an accepted recovery held by schedule, dependency, project enablement, catalog quota or shared capacity.
- **When** ticks evaluate it.
- **Then** it stays visibly awaiting-admission with a hold reason, and activates only when every gate passes using exactly one shared capacity slot.

### [AC-09] Concurrent ownership and expired workers

- **Given** two distinct recovery requests or ordinary PR enrollment compete with recovery and a worker outlives its lease.
- **When** they acquire locks and attempt activation.
- **Then** at most one recovery owns an Item, an active-owner race returns HTTP 409 or closes an accepted record refused, the loser sends zero deliveries, and stale workers cannot apply observations.

### [AC-10] Reuse observed implementation

- **Given** a terminal Run has a confirmed delivered implementation followed by a pushed head or external implementation evidence.
- **When** recovery reconciles the original owned PR.
- **Then** the same Run advances to current-head CI without another implementation delivery, preserving epoch, previous attempts and merge ownership.

### [AC-11] Confirmed merge and retention

- **Given** the original PR is correctly merged or its successful detailed Run is later pruned.
- **When** recovery/ordinary observation records success or retention runs.
- **Then** confirmed original-target merge releases dependents without spending budget; immutable recovery snapshots and stable execution identity survive Run deletion, and legacy rows gain no invented history.

### [AC-12] Operator recovery disclosure

- **Given** the operator inspects an eligible or refused Work Item in the existing Plan panel.
- **When** they confirm a reason, inspect history or lose the response.
- **Then** the UI shows original failure/target and persistent budgets, accepted/awaiting-admission/reconciling/running/refused states and actions, pages history, and reuses the same request identity through transport uncertainty.

## 5. Accepted design and implementation assumptions

The input premises match the current base: preparation failure has no retry API, Item has one Run, and Run resume increments epoch. Recovery therefore uses a distinct guarded owner entry. The recommended inline disclosure is retained; the separate-page alternative is not selected because dependency context stays visible. Planning UX findings are carried in the Screens draft.

### 5. Planning decisions

#### Options and recommendation

| Option | Benefit | Cost and risk | Decision |
| --- | --- | --- | --- |
| Retain Item and its PR run; typed durable recovery records | Existing request identities and attempt counters remain authoritative; old failure snapshots stay inspectable | Additive migration and a guarded PR-owner terminal recovery entry point | Recommended |
| Replace the linked PR run on every retry | Reuses ordinary enrollment | Resets per-run budgets and hides lineage unless another ledger is added; risks duplicate external work | Reject |
| Re-register a replacement Plan | Existing API requires no changes | Cannot satisfy the original dependencies and repeats successful work | Reject for this goal |

`ADR-work-item-recovery-lineage` records the durable design. Recovery is an
explicit operator request for unchanged work; specification, dependency and
target edits remain outside this command. No new PR run or automatic PR reopening
is introduced. This keeps the original Run budget and detailed history in place.

#### Eligibility and routing

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

#### Request, transaction and dispatch contract

- Add `POST /{plan_id}/items/{item_id}/recover` and paged `GET /{plan_id}/items/{item_id}/recoveries` under the existing Work Plan API. Read responses include eligibility and a machine-readable refusal reason with human next action. Use existing project application access and authenticated actor; accept no caller-supplied actor.
- Require UUID `request_id`, `expected_revision` for the Plan, `expected_run_revision` when linked, and trimmed `reason` of 1–500 characters. Scope request uniqueness to the project; digest includes Item, actor and normalized command including observed revisions. Equivalent replay returns the original recovery record and current Item even after revisions advance; changed identity content returns 409. Scope/access checks precede replay, and replay precedes stale-revision rejection.
- Persist one typed recovery record with immutable command, prior Item/Run outcome, PR/branch/head identities, actor, reason and accepted revisions. Append immutable outcome events for reconciliation, admission, dispatch or refusal; do not overwrite the prior snapshot. Existing Run attempts remain distinct from this Work Item recovery history.
- Atomically record recovery, Plan activity and revision increment; rollback all on failure. A pending record gives one recovery owner per Item. Rejected preflight requests do not reserve dispatch capacity. Identical duplicate requests do not add activity or counters.
- Implement a documented shared lock protocol covering recovery, observation, ordinary controls, admission and retention. Preserve Run-before-Item locking when both are held; never acquire Project/Plan after holding Item in an inverse order. Determine the complete existing acquisition order during Development and use transaction phases if required. Every phase rechecks Plan/Run revisions, lease generation and recovery identity before applying remote observations.
- Commit reconciliation intent/lease before remote reads, release DB locks for I/O, then reacquire and validate. Expired workers cannot mutate the Item or Run. Unknown reads retain a pending record and are retried by the existing tick; a definitive refusal closes the record with no dispatch.
- Recovery passes existing schedule, dependency, enabled-project, catalog/quota and shared capacity gates. A recovered Run reserves exactly one slot using ordinary PR ownership. Run activation and durable delivery intent commit together; worker crashes and response loss reconcile that intent before another send. Reuse existing external request identities for uncertain delivery, and allocate a fresh execution request only after a confirmed stopped prior delivery and remaining owner budget.
- The guarded PR-owner entry point accepts only terminal Runs linked to this Item and recovery record. It refuses when another active Run owns the PR, rechecks ownership atomically during activation, and translates the active-owner uniqueness race to HTTP 409 with no dispatch from the losing request. A losing pre-acceptance transaction rolls back its intent; an already accepted reconciliation record closes as refused without activating its Run. It never increments `run.epoch` or resets epoch-scoped repair allowances. It preserves existing attempt numbers, fix/silent/delivery counters and prior request snapshots; it does not broaden ordinary Run resume. No manual budget override is part of Item recovery. A merged observation can finish without spending budget. Reuse the PR owner’s pushed-head/external-implementation reconciliation: when that evidence applies, continue current-head CI observation without another implementation delivery, retaining the epoch and prior attempts. Regression checks cover exhausted-current-epoch refusal with unchanged epoch, recovery racing ordinary enrollment with zero loser deliveries, and terminal recovery after implementation arrived with zero new delivery.
- Successful predecessor Items and their merge evidence remain untouched. Dependents release only on the recovered Item's confirmed original-target merge. Existing retention protects the linked unresolved Run; successful pruning retains the recovery snapshots and stable execution identity without requiring the detailed Run row.

#### Migration and Development verification

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

#### Assumptions and review offer

Conservative eligibility above is the recommended direction, not a separate
business question. Unsupported recovery remains a visible refusal rather than
implicit replacement. Development effort stays high because persisted history
and external request fencing change. Optional UX review is offered for the
Screens drafts in `PROP-work-item-retry-target` before code; the Host can include
it in the direction review. This turn neither accepts nor hands off the proposal.


## 6. Screens


### Candidates

| Candidate | Primary region and task split | Trade-off |
| --- | --- | --- |
| Inline Item recovery disclosure in `UX-work-plans` | Current failure and recovery history beside the selected Item; review then confirm in place | Recommended: preserves dependency context and avoids changing tabs |
| Separate recovery page | A focused timeline and form reached from an Item link | More room for history but loses the surrounding successful work and adds navigation |

### Selected draft: `UX-work-plans` Item recovery disclosure

**Element:** panel extension. **Purpose:** recover unchanged failed work while
seeing its cause, eligibility and prior execution. Existing project tokens and
components provide visual style. The Item row remains primary; recovery history
is secondary and paged. This is an inline disclosure, not a separate modal.

**Content tree:**

- Work Plan summary: state, revision and dependency context.
  - Work Item selected row: failure, original target, PR/Run links, recovery eligibility and refusal explanation.
    - Work Item recovery disclosure when opened: prior result, reconciliation warning, reason field, confirm/cancel and response status.
    - Work Item recovery history: actor/time/reason, previous outcome, reconciliation/result events and retained execution links.
  - Successful Work Item siblings: retained results and links, unchanged by recovery.

**States:**

- `populated`: eligible Item shows “Retry Work Item”; inspect history or open disclosure.
- `ineligible`: show precise reason and supported next action: refresh evidence, resume Plan, open Run controls, or inspect closed/foreign work. Do not show a clickable retry for an unsupported outcome.
- `confirming`: show unchanged-work scope, target/PR, prior failure, reason and “Confirm retry”; cancel returns to the Item. Explain that successful Items stay complete and budget counters persist.
- `busy`: disable competing submissions, keep the same request identity through response loss and show “Checking recovery”.
- `awaiting-admission`: acceptance is confirmed; show the schedule, dependency, catalog/quota or capacity hold reason and refresh/status action. Retry stays disabled while this recovery is pending.
- `running`: show the retained Run link and active progress; inspect execution or close the disclosure.
- `reconciling`: show that no fresh request is sent until the previous outcome is known; refresh/status check remains available.
- `error`: preserve reason and request identity; stale evidence prompts reload and fresh confirmation, transport uncertainty prompts lookup/replay of the original request.
- `empty`: no recovery history; show the existing failure evidence and applicable action.
- `loading`: history/status loading; keep current Item context and allow closing the disclosure.

**Interactions:** proposed extension keys `4c` and `5c` will be added to
`UC-execute-work-plan`; the accepted use case will cite `UX-work-plans` back.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Retry Work Item | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c | populated | confirming | | `CAP-WORK-work-plan-execution` | Shows retained failure, original target and required reason |
| Confirm retry | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c | confirming | busy | | `CAP-WORK-work-plan-execution` | Acceptance appears; busy resolves to awaiting-admission with a hold reason, reconciling for uncertainty, running after admission, or ineligible after definitive refusal |
| Refresh recovery or response-loss status | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c | busy, awaiting-admission, reconciling, error | awaiting-admission, reconciling, running, ineligible | | `CAP-WORK-work-plan-execution` | Same identity recovers status without duplicate work |
| Open existing Run controls | `UC-execute-work-plan` 5a | ineligible | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | Existing Run owns pause, questions and ordinary resume |
| Inspect history / load next page | `UC-execute-work-plan` 7 | populated, empty | populated | | `CAP-WORK-work-plan-execution` | Prior outcomes remain distinguishable from current state |
| Cancel / close disclosure | `UC-execute-work-plan` 4c, `UC-execute-work-plan` 5c | confirming, populated, error, loading | populated | close | `CAP-WORK-work-plan-execution` | Returns to the Work Item without sending a command |

**Register changes:** extend the existing Work Item row in the UX object register
with recovery disclosure/history representations and retry, inspect history and
refresh recovery actions. Register a qualified Work Item recovery record in the
glossary only if exposed as a separately named domain object; do not reuse
Execution attempt for it.

