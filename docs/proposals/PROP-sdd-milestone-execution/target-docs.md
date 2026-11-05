---
id: PROP-sdd-milestone-execution-target
title: Living Spec targets for PROP-sdd-milestone-execution
summary: "Candidate contract and interface updates for execute selected sdd milestone work sequentially."
status: draft
proposal: PROP-sdd-milestone-execution
created_at: 2026-11-05
targets:
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/sdd/UX-sdd-execution.md
  - file: docs/steering/ux-objects.md
  - file: docs/architecture/ARCH-06-execution.md
---

# [Blueprint] PROP-sdd-milestone-execution: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend `CAP-SDD-native-delivery` with durable batch ownership and progression. Preserve `CAP-SDD-workflow-control` authority; describe any bounded maintenance driver in `CAP-EXEC-scheduling-maintenance`.

## 2. Use Cases and Interface Plan

Extend `UC-start-sdd-activity` and `UC-complete-sdd-workflow` with sequential batch, drift and control scenarios. Planning determines whether one dedicated batch use case/screen is warranted, then drafts it before code alongside `UX-sdd-execution`.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

Describe the coordinator and admission recovery in `ARCH-06-execution`. Planning chooses ledger and control semantics and records lasting architecture choices in PADRs where warranted.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: each eligible SDD activity needs an individual start. After: a durable selected batch starts successive activities under fresh evidence and existing approval boundaries.
