---
id: PROP-sdd-milestone-readiness-target
title: Living Spec targets for PROP-sdd-milestone-readiness
summary: "Candidate contract and interface updates for preview executable sdd milestone work."
status: draft
proposal: PROP-sdd-milestone-readiness
created_at: 2026-11-05
targets:
  - file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
  - file: docs/ux/repository/UX-repository.md
  - file: docs/ux/sdd/UX-sdd-execution.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] PROP-sdd-milestone-readiness: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Keep `CAP-DOC-repository-viewer` read-only. Extend `CAP-SDD-native-delivery` with a milestone selection/readiness interface and its observation-only guarantees.

## 2. Use Cases and Interface Plan

Extend `UC-inspect-repository-documents` and `UC-start-sdd-activity` with milestone preview and blocked-member examples. Draft a Hub-owned selection/readiness panel during Planning and reconcile its relationship to `UX-repository` and `UX-sdd-execution`.

Update the existing Work Item, SDD unit, PR run or Run question representations
in `docs/steering/ux-objects.md` where the accepted interface adds actions.
Register any distinct object only after checking the glossary during Planning.

## 3. Architecture and Decision Impact

Reuse repository reading and isolated SDD evaluation. No execution ledger or SDK ownership change is proposed.

## 4. Development Conventions and Governance

No devkit workflow, governance rule or toolchain change is proposed. Regenerate
the typed UI client if accepted API changes require it. Use existing API access
and owner-specific revision checks.

## 5. Before and After

Before: milestone members link to documents and individual starts. After: operators can inspect a bounded, revision-identified selection and exact readiness before any execution exists.
