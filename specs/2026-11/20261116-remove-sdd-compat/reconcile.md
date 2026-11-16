---
reconcile_id: REC-remove-sdd-compat
status: pending
targets:
  - file: docs/architecture/ARCH-02-constraints.md
    resolution: modified
  - file: docs/architecture/ARCH-05-2-components.md
    resolution: modified
  - file: docs/architecture/ARCH-06-execution.md
    resolution: modified
  - file: docs/architecture/ARCH-07-deployment.md
    resolution: modified
  - file: docs/architecture/ARCH-08-crosscutting-concepts.md
    resolution: modified
  - file: docs/architecture/ARCH-11-risks-and-technical-debt.md
    resolution: modified
  - file: docs/architecture/README.md
    resolution: modified
  - file: docs/capabilities/README.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-owed-items.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    resolution: modified
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
    resolution: modified
  - file: docs/capabilities/mcp/CAP-MCP-tool-access.md
    resolution: modified
  - file: docs/capabilities/notifications/CAP-NOTIFY-operator-notifications.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/capabilities/sdk/CAP-SDK-task-flow-execution.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-decision-continuation-outcomes.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-decision-inbox-read-projection.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-sdd-batch-ledger.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-offline-source-build.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-locked-runtime.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-owned-sdd-execution.md
    resolution: modified
  - file: docs/decisions/2026-11/20261113-repository-path-sources.md
    resolution: modified
  - file: docs/decisions/2026-11/20261116-remove-native-sdd-compatibility.md
    resolution: modified
  - file: docs/development/README.md
    resolution: modified
  - file: docs/development/testing.md
    resolution: modified
  - file: docs/development/toolchain.md
    resolution: modified
  - file: docs/operations/README.md
    resolution: modified
  - file: docs/operations/cloud-run-deployment.md
    resolution: modified
  - file: docs/operations/deployment-status.md
    resolution: modified
  - file: docs/operations/execution-targets.md
    resolution: modified
  - file: docs/operations/sdd-runtime.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/usecases/README.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/usecases/notifications/UC-receive-decision-notice.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
    resolution: modified
  - file: docs/usecases/sdk/UC-execute-task-flow.md
    resolution: modified
  - file: docs/ux/delivery/UX-attention.md
    resolution: modified
  - file: docs/ux/delivery/UX-decision-inbox.md
    resolution: modified
  - file: docs/ux/delivery/UX-run-decisions.md
    resolution: modified
  - file: docs/ux/delivery/UX-run-page.md
    resolution: modified
  - file: docs/ux/projects/UX-project-detail.md
    resolution: modified
  - file: docs/ux/repository/UX-repository.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-claim-recovery.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-execution.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-proposals.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-run.md
    resolution: modified
  - file: docs/ux/settings/UX-decision-subscription.md
    resolution: modified
---

# Native compatibility removal

Current contracts describe only repository-owned activities, ordinary PR questions and generic SDK workers.
Standalone claim recovery remains exact, project-scoped and limited to uncertain no-Run publication.
Deleted legacy-only contracts and screens:

- `docs/capabilities/sdd/CAP-SDD-runtime-isolation.md`
- `docs/capabilities/sdd/CAP-SDD-workflow-control.md`
- `docs/capabilities/sdk/CAP-SDK-existing-pr-bridge.md`
- `docs/usecases/sdd/UC-decide-sdd-proposal.md`
- `docs/usecases/sdd/UC-execute-sdd-batch.md`
- `docs/usecases/sdd/UC-preview-sdd-milestone.md`
- `docs/usecases/sdk/UC-resume-verified-pr.md`
- `docs/ux/sdd/UX-sdd-batch.md`
- `docs/ux/sdd/UX-sdd-decision-history.md`
- `docs/ux/sdd/UX-sdd-milestone-preview.md`
- `docs/ux/sdd/UX-sdd-workflow-request.md`

Historical document IDs resolve through aliases on surviving owners; no serving compatibility remains.
Migration revision identifiers remain valid, and a forward migration drops unused batch and bridge storage, native progress and decision evidence.
Completed specs remain unchanged apart from one reference-only repair in historical feedback,
which retains a deleted screen name as literal historical evidence. No required work is deferred.
