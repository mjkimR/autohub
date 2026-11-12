---
reconcile_id: REC-sdd-diagnostics-readiness
status: resolved
targets:
  - file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-execution.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-run.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
---

# Reconciliation: SDD diagnostics and readiness

The runtime contract owns bounded Hub-authored diagnostics, unknown-content handling and separation from semantic execution identity. The workflow contract owns read-only registration context and selected-combination invalidation. The use case and existing execution panels expose that behavior without adding authority or action channels.

The Screens drafts are reflected in the two existing UX documents and the shared object representations. No new domain concept or architectural layer is introduced. The parent Run Decisions modal remains unchanged because its existing native-panel reference already covers this evidence region.

The source and cited regression assertions were inspected. Actual executed check results and implementation review remain in workflow envelopes; this record does not claim deployment or live-provider evidence. No agreed requirement is deferred.

Entrypoint derivation proposed task-boundary directories, test trees and generated API paths. These candidates are rejected: the existing service/controller/API doorway files still own this behavior, and the diagnostic and preview helpers do not create a new operation entrypoint.
