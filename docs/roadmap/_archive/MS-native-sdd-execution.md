---
id: MS-native-sdd-execution
title: Execute native SDD milestones sequentially
summary: "Connect repository milestones to sequential native SDD execution. Exit requires inspectable selection, dependency-aware progression and recoverable batch controls under existing decision authority."
status: done
created_at: 2026-11-05
depends_on: []
---

# [MS-native-sdd-execution] Execute native SDD milestones sequentially

## Goal

Support native repository delivery in [Product context](../../steering/product.md)
under `ARCH-03-system-context` ownership. Let an operator progress selected
milestone members without manually finding and starting each subsequent SDD unit.

## Exit condition

- An operator can inspect milestone members, their selected repository basis,
  executable activities and dependency or eligibility holds before starting work.
- A requested batch progresses selected units sequentially and re-evaluates
  current repository evidence before each activity starts.
- Existing proposal, handoff and integration decisions remain effective. A batch
  start does not approve future decisions.
- Batch pause or stop prevents subsequent starts; already admitted activities
  retain their controls and evidence. Resumption reconciles existing activity
  identities before continuing.

These outcomes connect `CAP-DOC-repository-viewer` to
`CAP-SDD-native-delivery` and `CAP-SDD-workflow-control`. They do not make the
read-only viewer an execution owner.

## Non-goals

- **Scope Excluded**: parallel SDD execution, multiple proposals on one activity
  branch, automatic decomposition and inferred dependencies.
- **Scope Excluded**: duplicating proposal/spec specifications into Work Plans,
  a second PR merge controller and SDK flow orchestration.
- **Scope Excluded**: deployment, production verification, monitoring and CI
  configuration.

## Completion review

Decomposition: confirmed
Direct proposal work: confirmed

The completed scope covers the full exit condition through completed
`SPEC-sdd-milestone-readiness` and `SPEC-sdd-milestone-execution`. Read-only
readiness inspection and explicit sequential execution retain native decision
authority, admission identities and future-admission controls. No unresolved
direct proposal or unfinished handed-off work remains in this scope.
