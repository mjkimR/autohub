---
reconcile_id: REC-sdd-unit-experience
status: resolved
targets:
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-proposals.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-execution.md
    resolution: modified
  - file: docs/ux/repository/UX-repository.md
    resolution: modified
  - file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
    resolution: modified
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
---

# Reconciliation

Reflect selected-unit activity/enrollment/history, path/ref navigation, independent original-request recovery and progressive session-cached reads. APIs, runtime ownership and stored execution semantics are unchanged. No architecture invariant or ADR changes.

Verification: source/test inspection and executed checks are separate. UI checks use fixtures; browser host access was unavailable, so no rendered desktop/mobile or live GitHub verification is claimed. No required work is deferred. A persistent backend document index is an explicit non-goal.

Entrypoint review: retain existing repository/API doorways and add SddUnitActions.svelte to the start/follow use cases. Reject the broad repositories directory candidate and helper/test paths. Existing capability and inspection doorways already lead to the changed components.
