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

Extend `CAP-WORK-work-plan-execution` with explicit replacement identity and scoped dependency satisfaction. Replace the existing blanket exclusion only for the accepted narrow relationship.

## 2. Use Cases and Interface Plan

Extend `UC-execute-work-plan` with link, inspect and accept-replacement-result examples. Extend `UX-work-plans` with original/replacement evidence and a separate dependency-satisfaction action. Draft its review interaction during Planning.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

Extend `ARCH-06-execution` with replacement evidence ownership. Planning resolves replacement semantics and records a PADR if the selected lasting decision warrants one.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: replacements have descriptive links and cannot fulfill original dependencies. After: recorded relationships support explicit, reviewed dependency satisfaction while preserving both outcomes.
