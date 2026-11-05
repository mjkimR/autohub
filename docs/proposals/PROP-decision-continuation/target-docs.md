---
id: PROP-decision-continuation-target
title: Living Spec targets for PROP-decision-continuation
summary: "Candidate contract and interface updates for follow decisions through explicit continuation."
status: draft
proposal: PROP-decision-continuation
created_at: 2026-11-05
targets:
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/usecases/delivery/UC-resolve-run-question.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/delivery/UX-run-decisions.md
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
  - file: docs/ux/sdd/UX-sdd-run.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] PROP-decision-continuation: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend outcome disclosure and continuation navigation while preserving the save/apply and decision/publication guarantees in the existing owning capabilities.

## 2. Use Cases and Interface Plan

Extend `UC-resolve-run-question` and `UC-complete-sdd-workflow` with post-decision continuation, uncertainty and stale-context examples. Draft the changed state/action regions of `UX-run-decisions`, `UX-sdd-workflow-request` and `UX-sdd-run` during Planning.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

No replacement approval or execution controller is proposed. Planning identifies the minimum owner read-model changes needed for truthful outcome disclosure.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: a completed save or decision can require locating a separate continuation action. After: the reviewed context shows the actual outcome and its explicit owner-authorized next step.
