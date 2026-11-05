---
id: PROP-work-item-retry-target
title: Living Spec targets for PROP-work-item-retry
summary: "Candidate contract and interface updates for retry failed work items."
status: draft
proposal: PROP-work-item-retry
created_at: 2026-11-05
targets:
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
