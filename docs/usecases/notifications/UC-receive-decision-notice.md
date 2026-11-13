---
id: UC-receive-decision-notice
title: Review a decision from an operator notice
summary: "An operator follows a minimal observed notice to exact authenticated owner review and inspects transport uncertainty separately from decision progress."
area: notifications
primary_actor: Operator
supporting_actors: [Telegram]
status: active
capabilities:
  - CAP-NOTIFY-operator-notifications
  - CAP-PR-operator-decisions
entrypoints:
  - modules/hub/app/features/notifications/decision_api.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/discovery.py
---

# [UC-receive-decision-notice] Review a decision from an operator notice

## 1. Goal

- **Goal**: Reach the exact owner review from a trusted notice and understand its delivery evidence.
- **Trigger**: The operator receives a notice or inspects its retained history.
- **Preconditions**: A trusted Notification channel and Decision subscription exist.

## 2. Main Success Scenario

1. The operator follows the exact observed notice link (`CAP-NOTIFY-operator-notifications`). Screen: `UX-sign-in` when required, then `UX-decision-inbox`; retained links are also available in `UX-decision-notice-history`.
2. Hub authenticates and resolves the exact current subject before owner review (`CAP-PR-operator-decisions`). Screen: `UX-decision-inbox`.
3. The operator inspects the selected ordinary question and chooses an explicit owner action (`CAP-PR-operator-decisions`). Screen: `UX-decision-inbox`; the selected owner dialog continues `UC-resolve-run-question`. Retained native decisions provide history without approval or workflow actions.
4. The operator inspects delivery evidence and explicitly reviews any resend (`CAP-NOTIFY-operator-notifications`). Screen: `UX-notifications`, `UX-decision-notice-history`.

## 3. Extensions

- **1a.** The link is malformed: no exact request is sent; Open inbox ends the selection flow. Screen: `UX-decision-inbox`.
- **1b.** Sign-in is required: password preserves the requested URL; approved Google completion restores only a validated tab-local identity. Expired, missing, invalid or denied storage offers conditional guidance to reopen the original notice after successful authentication. Pending/rejected/cancelled/failed authentication opens no review. Screen: `UX-sign-in`.
- **2a.** The subject changed, resolved or became unavailable: explain it and offer Refresh inbox without substituting another subject. Screen: `UX-decision-inbox`.
- **2b.** Exact inspection fails: offer Retry review or Open inbox; no mutation is performed. Screen: `UX-decision-inbox`.
- **4a.** Delivery or resend command outcome is unknown: explain possible duplicate delivery; Check outcome or Retry same resend retains the original command. A separately reviewed Send again requires explicit duplicate acknowledgement. Screen: `UX-decision-notice-history`.
- **4b.** A generation is superseded or its subject unavailable: retain evidence, refuse resend and offer Open inbox. Screen: `UX-decision-notice-history`.
- **4c.** Subscription or destination evidence changed: refuse stale resend and require refreshed explicit review. Screen: `UX-decision-notice-history`.

## 4. Postconditions

- **Success guarantee**: Only the matching authenticated subject opens; delivery evidence remains separate from owner decision progress.
- **Minimal guarantee**: Notice failures or stale links grant no authority and select no replacement. Unknown transport is never automatically resent.

## 5. Acceptance Criteria (Given / When / Then)

Rules: exact indexed selection and owner authority from `CAP-PR-operator-decisions`; explicit subscription, transport uncertainty and request replay from `CAP-NOTIFY-operator-notifications`.

### Scenario: Open exact work outside the first inbox page

- **Covers**: main success scenario.
- **Given**: A current exact notice identity outside the loaded list page.
- **When**: The authenticated operator follows the link.
- **Then**: Direct lookup selects the matching owner without pagination scans or provider discovery.
- **Test**: `modules/hub/tests/integration/features/notifications/test_decision_notices.py`; `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.integration.test.ts`.

### Scenario: Refuse obsolete selection without substitution

- **Covers**: 1a, 2a, 2b.
- **Given**: A malformed, changed, missing or unreadable subject.
- **When**: The operator follows its link.
- **Then**: Explicit recovery appears and another subject never opens automatically.
- **Test**: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.integration.test.ts`.

### Scenario: Recover bounded login navigation

- **Covers**: 1b.
- **Given**: Password or approved Google admission, with valid or unusable retained notice identity.
- **When**: Authentication succeeds.
- **Then**: A valid identity returns only to same-origin Decisions; unavailable identity offers reopen guidance without blocking sign-in.
- **Test**: `modules/hub-ui/src/lib/features/auth/login/notice-return.integration.test.ts`; `GoogleLogin.integration.test.ts`; `LoginView.integration.test.ts` in the same directory.

### Scenario: Review uncertain delivery separately

- **Covers**: 4a, 4b, 4c.
- **Given**: Unknown delivery, superseded work or changed subscription evidence.
- **When**: The operator reviews Send again.
- **Then**: Current basis and duplicate risk are visible; stale/ineligible admission is refused and exact request replay creates no extra attempt.
- **Test**: `modules/hub/tests/integration/features/notifications/test_decision_notices.py`; `modules/hub-ui/src/lib/features/configuration/notifications/DecisionNotices.integration.test.ts`.
