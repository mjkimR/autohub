---
id: UX-app-shell
title: Authenticated navigation panel
summary: "Provide navigation, health indication and session controls around each authenticated management screen. Supports exact pending-decision navigation."
area: navigation
element: panel
status: active
usecases:
  - UC-access-hub
capabilities:
  - CAP-ACCESS-authentication-authorization
---

# [UX-app-shell] Authenticated navigation panel

## 1. Purpose

- **Primary task**: navigate the management console within an admitted Browser session.
- **Facts to commit**: the active destination, API-session status and Core Online/Offline indicator.
- **Secondary items**: administrative links appear after the profile identifies a superadministrator; feature content stays in the selected screen.

## 2. Content

The navigation is secondary to the active screen. It is a persistent side region on wide displays and a Menu-controlled region on narrow displays.

- Browser session (status badge): Active and Logout.
- Browser session (navigation context): current route label and active link.
- Project connection and PR run (destinations): Projects and Pipeline runs.
- Schedule configuration and Schedule job (destinations): Schedule configs and Schedule jobs.
- Connector and AI catalog (destinations): configuration links, alongside notification and system settings.
- Account and Machine key (administrative destinations): Account approval and Machine keys when the profile allows them.
- Service health (indicator): a periodic shallow health check reports Core Online or Offline.
- Theme preference (toggle): also accessible in the narrow header.

Decisions opens `UX-decision-inbox` from the project management navigation and highlights the current destination.

## 3. States

- **populated**: authenticated children and navigation remain usable; choose a destination or Logout.
- **menu-open**: narrow navigation is expanded; selecting another URL implicitly closes its route-bound menu state.
- **offline**: the health indicator changes without itself removing the session or navigation.
- **sign-out-error**: a failed logout produces a toast; the operator can retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Decisions | global: navigate to pending operator work | populated | populated | `UX-decision-inbox` | | The cross-project worklist opens. |
| Display the admitted console | `UC-access-hub` 2, `UC-access-hub` 3 | populated | populated |  | `CAP-ACCESS-authentication-authorization` | The requested feature screen is rendered inside the shell. |
| Logout | `UC-access-hub` 5 | populated | populated | `UX-sign-in` | `CAP-ACCESS-authentication-authorization` | Successful logout replaces the shell with the sign-in screen; failure is a toast. |
| Open Dashboard | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | System Overview becomes the selected screen. |
| Open Projects | global: navigation between management surfaces | populated | populated | `UX-projects` |  | The project list becomes the selected screen. |
| Open Pipeline runs | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | The run list becomes the selected screen. |
| Open Schedule configs | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule configurations appear. |
| Open Schedule jobs | global: navigation between management surfaces | populated | populated | `UX-schedule-jobs` |  | Schedule-job history appears. |
| Open Connectors | global: navigation between management surfaces | populated | populated | `UX-connectors` |  | Connector configuration appears. |
| Open AI Catalogs | global: navigation between management surfaces | populated | populated | `UX-ai-catalogs` |  | AI catalog configuration appears. |
| Open Notifications | global: navigation between management surfaces | populated | populated | `UX-notifications` |  | Notification channels appear. |
| Open System configs | global: navigation between management surfaces | populated | populated | `UX-system-settings` |  | Read-only configuration records appear. |
| Open Task specs | global: navigation between management surfaces | populated | populated | `UX-task-specs` |  | Registered task specifications appear. |
| Open Webhook deliveries | global: navigation between management surfaces | populated | populated | `UX-webhook-deliveries` |  | Webhook delivery history appears. |
| Open Account approval | global: navigation between management surfaces | populated | populated | `UX-users` | `CAP-ACCESS-authentication-authorization` | The account table appears. |
| Open Machine keys | global: navigation between management surfaces | populated | populated | `UX-machines` | `CAP-ACCESS-authentication-authorization` | Machine administration appears. |
| Toggle Menu | global: reveal navigation on narrow displays | populated | menu-open |  |  | Menu expansion is reflected by aria-expanded. |
| Toggle theme | global: a console-wide visual preference | populated | populated |  |  | The theme changes without changing the current task. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/components/shared/AppShell.svelte` and `modules/hub-ui/src/routes/+layout.svelte`. Session behavior is covered by the inspected `modules/hub-ui/src/lib/api/client.test.ts` and `modules/hub-ui/src/lib/stores/session.test.ts`.
