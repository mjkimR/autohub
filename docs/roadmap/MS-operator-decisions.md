---
id: MS-operator-decisions
title: Complete operator decisions across projects
summary: "Bring pending PR questions and native SDD decisions into one operator task flow. Exit requires current decision context, explicit authorization and visible continuation outcomes."
status: planned
created_at: 2026-11-05
depends_on: []
---

# [MS-operator-decisions] Complete operator decisions across projects

## Goal

Support human decisions in the delivery paths described by
[Product context](../steering/product.md) and preserve the separate authority
subjects in `ARCH-03-system-context`. Let an operator find actionable questions
and approvals across projects and follow a decision to its permitted next step.

## Exit condition

- An operator can find pending ordinary PR questions and native SDD decisions
  across accessible projects without visiting each project's execution list.
- Each decision exposes its owning run, question or workflow request, reviewed
  evidence and the operation being authorized.
- Changed evidence requires refreshed inspection instead of applying stale
  authority. Saved answers and approval records remain distinct from execution.
- After a decision, the operator can inspect whether it was saved, applied,
  awaiting publication, awaiting delivery or blocked, and take the applicable
  explicit next action without searching unrelated screens.

These outcomes compose `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`
and `CAP-SDD-workflow-control` without replacing their mutation boundaries.

## Non-goals

- **Scope Excluded**: bulk approval, implicit resume on answer save, automatic
  approval of changed evidence and merging distinct authorization subjects.
- **Scope Excluded**: Jules provider questions, SDK machine approvals, account
  administration and Telegram commands.
- **Scope Excluded**: health dashboards, monitoring, incident detection,
  deployment and production verification.

## Completion review

Decomposition: pending
Direct proposal work: pending
