---
id: MS-batch-recovery
title: Recover partially completed Work Plans
summary: "Let operators finish partially failed Work Plans without repeating successful work. Exit requires recoverable failed Items and explicit replacement relationships that preserve execution evidence."
status: planned
created_at: 2026-11-05
depends_on: []
---

# [MS-batch-recovery] Recover partially completed Work Plans

## Goal

Support the operator's batch delivery goal in [Product context](../steering/product.md)
within the execution ownership described by `ARCH-03-system-context`. Let an
operator continue a partially completed Work Plan while retaining successful
results and the evidence of failed or superseded work.

## Exit condition

- An operator can recover an eligible failed Work Item without recreating its
  entire Work Plan or repeating successful predecessor Items.
- Recovery preserves prior attempts and reconciles uncertain external effects
  before requesting more work.
- An operator can explicitly relate replacement work to its original and inspect
  whether that relationship satisfies downstream dependencies.
- Replacement success does not rewrite the original outcome or silently release
  dependencies. PR execution and merge authority retain their existing owners.

These outcomes extend `CAP-WORK-work-plan-execution` and preserve
`CAP-PR-pull-request-delivery` ownership. Planning defines eligible recovery and
replacement cases.

## Non-goals

- **Scope Excluded**: automatic replacement selection, rollback of remote effects,
  general cross-Plan Item dependency graphs and automatic work decomposition.
- **Scope Excluded**: native SDD batch execution, provider routing, deployment,
  production verification, monitoring and CI configuration.

## Completion review

Decomposition: pending
Direct proposal work: pending
