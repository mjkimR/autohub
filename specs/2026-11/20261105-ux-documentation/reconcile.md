---
reconcile_id: REC-ux-documentation
status: resolved
targets:
  - file: docs/README.md
    resolution: modified
  - file: docs/operations/README.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/usecases/access/UC-access-hub.md
    resolution: modified
  - file: docs/usecases/agents/UC-configure-agent-catalog.md
    resolution: modified
  - file: docs/usecases/agents/UC-run-agent-session.md
    resolution: modified
  - file: docs/usecases/connections/UC-verify-project-connection.md
    resolution: modified
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/usecases/notifications/UC-configure-operator-notifications.md
    resolution: modified
  - file: docs/usecases/projects/UC-configure-project-connection.md
    resolution: modified
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
    resolution: modified
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
    resolution: modified
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
    resolution: modified
  - file: docs/ux/README.md
    resolution: modified
  - file: docs/ux/access/UX-issued-machine-key.md
    resolution: modified
  - file: docs/ux/access/UX-machine-keys.md
    resolution: modified
  - file: docs/ux/access/UX-machines.md
    resolution: modified
  - file: docs/ux/access/UX-sign-in.md
    resolution: modified
  - file: docs/ux/access/UX-users.md
    resolution: modified
  - file: docs/ux/agents/UX-ai-catalogs.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-availability.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-codex-refresh.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-concurrency.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-connector.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-create.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-daily-quota.md
    resolution: modified
  - file: docs/ux/agents/UX-catalog-sessions.md
    resolution: modified
  - file: docs/ux/connections/UX-connector-create.md
    resolution: modified
  - file: docs/ux/connections/UX-connector-edit.md
    resolution: modified
  - file: docs/ux/connections/UX-connectors.md
    resolution: modified
  - file: docs/ux/delivery/UX-attach-pull-request.md
    resolution: modified
  - file: docs/ux/delivery/UX-attempt-history.md
    resolution: modified
  - file: docs/ux/delivery/UX-enroll-pull-request.md
    resolution: modified
  - file: docs/ux/delivery/UX-pipeline-runs.md
    resolution: modified
  - file: docs/ux/delivery/UX-run-decisions.md
    resolution: modified
  - file: docs/ux/execution/UX-schedule-configs.md
    resolution: modified
  - file: docs/ux/execution/UX-schedule-delete.md
    resolution: modified
  - file: docs/ux/execution/UX-schedule-editor.md
    resolution: modified
  - file: docs/ux/execution/UX-schedule-jobs.md
    resolution: modified
  - file: docs/ux/execution/UX-task-specs.md
    resolution: modified
  - file: docs/ux/navigation/UX-app-shell.md
    resolution: modified
  - file: docs/ux/operations/UX-dashboard.md
    resolution: modified
  - file: docs/ux/operations/UX-webhook-deliveries.md
    resolution: modified
  - file: docs/ux/projects/UX-agent-schedules.md
    resolution: modified
  - file: docs/ux/projects/UX-connection-test-check.md
    resolution: modified
  - file: docs/ux/projects/UX-connection-tests.md
    resolution: modified
  - file: docs/ux/projects/UX-project-connections.md
    resolution: modified
  - file: docs/ux/projects/UX-project-create.md
    resolution: modified
  - file: docs/ux/projects/UX-project-detail.md
    resolution: modified
  - file: docs/ux/projects/UX-project-schedule.md
    resolution: modified
  - file: docs/ux/projects/UX-project-settings.md
    resolution: modified
  - file: docs/ux/projects/UX-projects.md
    resolution: modified
  - file: docs/ux/repository/UX-repository.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-decision-history.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-execution.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-proposals.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-run.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
    resolution: modified
  - file: docs/ux/settings/UX-notification-editor.md
    resolution: modified
  - file: docs/ux/settings/UX-notifications.md
    resolution: modified
  - file: docs/ux/settings/UX-system-settings.md
    resolution: modified
  - file: docs/ux/work-plans/UX-work-plan-editor.md
    resolution: modified
  - file: docs/ux/work-plans/UX-work-plans.md
    resolution: modified
---

# UX documentation reconciliation

All targets are present in the branch diff. The shared object register and
glossary distinguish interface representations from domain definitions; each
retained UI element is documented with source evidence. Thirteen existing use
cases gain reciprocal screen citations or specific off-screen reasons without
changing their actor goals, capability guarantees or acceptance outcomes.

The UX index accounts for all fourteen route views and layout-based sign-in.
API-only CI/MCP/SDK goals remain outside the browser inventory. The operations
index explains repeatable procedures versus dated material evidence; no operating
procedure was moved into materials.

No product code, runtime policy, capability or architecture contract changes.
Source inspection and independent reviews are recorded separately from browser
execution, accessibility assessment and live-provider checks, which were not run.
No deferred product work or source-feedback item was part of this change.
