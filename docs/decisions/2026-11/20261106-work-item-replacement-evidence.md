---
id: ADR-work-item-replacement-evidence
title: Accept replacement evidence for one dependency
summary: "For replacement work, we accept confirmed merge evidence per existing Item dependency, to unblock reviewed work without rewriting outcomes, accepting explicit edge-by-edge review."
proposal: SPEC-work-item-replacement
status: accepted
created_at: 2026-11-05
---

# [ADR-work-item-replacement-evidence] Accept replacement evidence for one dependency

- **Status**: Accepted
- **Date**: 2026-11-05

---

## 1. Context & Problem Statement

Replacement registrations retain independent execution. Operators cannot release
an existing dependent with replacement evidence without recreating work.
Changing original outcomes would misstate completion and PR ownership.

## 2. Decision Drivers

- Preserve original outcomes and ordinary PR authority.
- Release only explicitly reviewed existing dependencies.
- Serialize withdrawal and consumption with admission.
- Retain evidence after detailed Run pruning.

## 3. Considered Options

- Typed link plus per-edge acceptance: explicit durable release with schema cost.
- Descriptive links only: no migration, but dependent recreation remains manual.
- General cross-Plan graph or successor substitution: broad automation with new
  graph semantics and implied equivalence beyond the requested boundary.

## 4. Decision Outcome

The chosen option is typed links plus per-existing-Item-edge acceptance.

- Replacement links preserve original Work Item and Work Plan outcomes and PR
  ownership. → `CAP-WORK-work-plan-execution` replacement evidence (MUST).
- Acceptance uses a replacement's confirmed same-repository/target merge only
  for the named existing local Item dependency. → `CAP-WORK-work-plan-execution`
  scoped satisfaction (MUST).
- Linking alone releases nothing; whole-Plan dependencies and other admission
  fences remain effective. → `CAP-WORK-work-plan-execution` scoped satisfaction (MUST).
- Chains are refused, and consumption prevents later withdrawal from falsifying
  admission evidence. → `CAP-WORK-work-plan-execution` replacement lifecycle (MUST).
- Typed evidence and consumption events commit atomically under project
  ownership with retained merge snapshots. → `ARCH-06-execution` replacement
  evidence structure (MUST).

## 5. Consequences

Explicit per-edge review costs operator time. Whole-Plan dependents of revoked
Plans still need a separate supported workflow. Retained endpoint roles make
chains unavailable after withdrawal; an original can choose a distinct candidate
after withdrawing an unconsumed link. The additive migration
creates no historical equivalence claims. The accepted retry foundation must
be revalidated against its landed completed spec before handoff.

## 6. Confirmation

`CAP-WORK-work-plan-execution` rules 37–45 and `ARCH-06-execution` replacement evidence structure restate the decision. `test_replacements.py` enforces exact-edge release, immutable replay, retained endpoint roles, merge identity, other admission gates, activity rollback and PostgreSQL control/withdrawal/admission races. `test_work_replacements.py` checks the additive migration. `WorkItemReplacement.integration.test.ts` verifies explicit review, persisted exact retry and paged retained history.

`SPEC-work-item-replacement` retains code-review, reconciliation and executed check results. The descriptive no-acceptance regression remains enforced. Controlled fixtures and PostgreSQL tests do not establish live provider or deployment behavior.
