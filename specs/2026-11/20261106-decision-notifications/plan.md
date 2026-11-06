---
id: PLAN-decision-notifications
spec: SPEC-decision-notifications
---
<!-- devkit:skeleton -->

# Technical Plan: `SPEC-decision-notifications` Notify operators about actionable delivery decisions

## 1. Architecture Overview & Impact
- Target Area: capabilities/notifications/
- Target Docs Blueprint: `PROP-decision-notifications-target` (Living Spec targets for this plan and reconcile.md)

## 2. Component Breakdown & Interface Contracts

### Planned Boundaries:
- `modules/hub/app/features/notifications/`
- `modules/hub/app/features/execution/tasks/domains/maintenance/task.py`
- `modules/hub/app/features/execution/tasks/domains/maintenance/`
- `modules/hub/migrations/versions/`
- `modules/hub/tests/integration/features/notifications/`
- `modules/hub/tests/integration/features/execution/maintenance/`
- `modules/hub/tests/integration/migrations/`
- `modules/hub-ui/src/lib/features/configuration/notifications/`
- `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.svelte`
- `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.integration.test.ts`
- `modules/hub-ui/src/lib/api/generated/notification-channel.d.ts`
- `modules/hub-ui/src/lib/api/generated/pipeline-run.d.ts`
- `modules/hub-ui/src/lib/api/generated/index.d.ts`
- `docs/capabilities/notifications/`
- `docs/usecases/notifications/`
- `docs/usecases/delivery/UC-resolve-run-question.md`
- `docs/usecases/sdd/UC-decide-sdd-proposal.md`
- `docs/usecases/sdd/UC-complete-sdd-workflow.md`
- `docs/ux/settings/UX-notifications.md`
- `docs/ux/settings/`
- `docs/ux/delivery/UX-decision-inbox.md`
- `docs/steering/ux-objects.md`
- `docs/steering/glossary.md`
- `docs/architecture/ARCH-06-execution.md`
- `modules/hub/app/features/project_management/pipeline_runs/api/v1.py`
- `modules/hub/app/features/project_management/pipeline_runs/usecases/discovery.py`
- `modules/hub/app/features/project_management/pipeline_runs/discovery_repo.py`
- `modules/hub/tests/integration/features/project_management/pipeline_runs/test_discovery.py`
- `modules/hub-ui/src/lib/features/auth/login/GoogleLogin.svelte`
- `modules/hub-ui/src/lib/features/auth/login/GoogleLogin.integration.test.ts`
- `modules/hub-ui/src/lib/features/auth/login/LoginView.svelte`
- `modules/hub-ui/src/lib/features/auth/login/LoginView.integration.test.ts`
- `modules/hub-ui/src/lib/features/auth/login/`
- `docs/usecases/access/UC-access-hub.md`
- `docs/ux/access/UX-sign-in.md`
- `docs/capabilities/delivery/CAP-PR-operator-decisions.md`

### Excluded Boundaries:
- `docs/operations/`
- `.github/`
- `packages/sdk/`

## 3. Verification & Test Plan
- <commands and checks that verify the acceptance criteria>
