---
id: PROP-work-item-retry-target
title: Living Spec targets for PROP-work-item-retry
summary: "Candidate contract and interface updates for retry failed work items."
status: draft
proposal: PROP-work-item-retry
created_at: 2026-11-05
targets:
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
  - file: docs/ux/work-plans/UX-work-plans.md
  - file: docs/steering/ux-objects.md
  - file: docs/architecture/ARCH-06-execution.md
---

# [Blueprint] PROP-work-item-retry: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend `CAP-WORK-work-plan-execution` with recovery eligibility, retained attempt identity, idempotency and dependency release. Preserve `CAP-PR-pull-request-delivery` ownership.

## 2. Use Cases and Interface Plan

Extend `UC-execute-work-plan` with recovery, refusal and response-loss scenarios. Extend `UX-work-plans` with eligible recovery actions, prior attempt links and explicit reconciliation holds. Draft the recovery interaction during Planning before code.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

Describe recovery history and reconciliation in `ARCH-06-execution`. Planning decides whether a retained recovery record needs an ADR; this draft makes no schema decision.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: failed Items require replacement registration. After: eligible failures can recover within the original Work Plan with inspectable prior attempts.

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

## 7. Contract and decision reflection

`CAP-WORK-work-plan-execution` removes only its failed-Item retry exclusion and
adds the exact eligibility/refusal matrix, atomic request identity, history,
fencing and dependency rules from the proposal. `UC-execute-work-plan` gains
`4c` preparation recovery and `5c` terminal delivery recovery, with examples for
uncertainty, replay, unchanged successful predecessors and exhaustion.

`CAP-PR-pull-request-delivery` and `UC-deliver-pull-request` distinguish the guarded
Work Item recovery entry from ordinary paused/blocked resume. Their owner retains
request reconciliation, counter enforcement and merge authority. This does not
change CI triggers or add a delivery engine.

`ARCH-06-execution` describes the additive record/event tables, shared lock
protocol and durable transition fencing. Promote `PADR-work-item-recovery-lineage`
only during authorized handoff. Preserve its rule traces when final section names
are chosen. No operational procedure, rollout or monitoring document is a target.

UX round 1 finding was folded into the awaiting-admission and running states and
explicit acceptance transitions. The original finding remains in `ux-review-01`
for the Host direction review, as Planning does not close UX findings by reverify.
