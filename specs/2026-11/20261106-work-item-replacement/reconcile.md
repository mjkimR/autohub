---
reconcile_id: REC-work-item-replacement
status: pending
targets:
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
    resolution: modified
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
    resolution: modified
  - file: docs/ux/work-plans/UX-work-plans.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/architecture/ARCH-06-execution.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-work-item-replacement-evidence.md
    resolution: modified
---

# Replacement reconciliation

The five blueprint targets, qualified glossary terms and Host-authorized ADR Confirmation reflect the reviewed implementation. No required scope is deferred. Existing API and execution doorway entrypoints remain appropriate; replacement helpers are reached through those owner entrypoints. Before/after uses one controlled dependency fixture: linking leaves zero released edges; explicit acceptance releases only one selected edge. Evidence is controlled integration/UI/PostgreSQL execution, not live deployment.
