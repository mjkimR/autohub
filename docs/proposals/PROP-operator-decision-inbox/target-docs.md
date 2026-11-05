---
id: PROP-operator-decision-inbox-target
title: Living Spec targets for PROP-operator-decision-inbox
summary: "Candidate contract and interface updates for find pending delivery decisions across projects."
status: draft
proposal: PROP-operator-decision-inbox
created_at: 2026-11-05
targets:
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/usecases/delivery/UC-resolve-run-question.md
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/delivery/UX-run-decisions.md
  - file: docs/ux/navigation/UX-app-shell.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] PROP-operator-decision-inbox: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Describe discovery guarantees in the existing decision-owning capabilities. Retain each capability's current mutation and approval boundaries.

## 2. Use Cases and Interface Plan

Connect `UC-resolve-run-question`, `UC-decide-sdd-proposal` and `UC-complete-sdd-workflow` to one worklist entry point. During Planning, draft the decision worklist and its navigation relationship to `UX-app-shell` and `UX-run-decisions`.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

Reuse owner-specific records and authorization. Planning resolves a bounded read projection and whether its structure needs an architecture update.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: decision discovery starts from individual project/run screens. After: one paginated cross-project worklist opens refreshed owner-specific decision contexts.
