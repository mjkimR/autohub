---
id: PLAN-decision-notifications
spec: SPEC-decision-notifications
---

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
- Run focused notification/discovery/auth UI and PostgreSQL admission/lease/migration tests, then `just lint`, `just check`, typed API and generated checks.
- Baseline: disabled subscription produces zero decision-specific sends; enabled matching subscription produces one admitted generation.

## Implementation design

Notification-owned subscription, generation, attempt and request receipt tables use channel-first locking. Repositories own queries, services own domain validation/admission, UseCases own transactions and network calls. Structured Telegram outcomes are separate from generic notices. Exact selection extends existing discovery with an indexed read. UI settings and immutable command state are separate components; auth navigation stores only a validated notice selection. Shared maintenance invokes bounded notification work after existing owners.
