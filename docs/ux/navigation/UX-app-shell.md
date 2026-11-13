---
id: UX-app-shell
title: Authenticated navigation panel
summary: "Provide navigation, health indication and session controls around each authenticated management screen, and signal operator-owed decisions from any screen. Supports exact pending-decision navigation."
area: navigation
element: panel
status: active
usecases:
  - UC-access-hub
capabilities:
  - CAP-ACCESS-authentication-authorization
  - CAP-PR-operator-decisions
---

# [UX-app-shell] Authenticated navigation panel

## 1. Purpose

- **Primary task**: navigate the management console within an admitted Browser session.
- **Facts to commit**: the active destination, API-session status, Core Online/Offline indicator and, while any are owed, the pending-decision count; while the count is unknown, a neutral mark that says so.
- **Secondary items**: administrative links appear after the profile identifies a superadministrator; feature content stays in the selected screen.

## 2. Content

The navigation is secondary to the active screen. It is a persistent side region on wide displays and a Menu-controlled region on narrow displays.

- Browser session (status badge): Active and Logout.
- Browser session (navigation context): current route label and active link.
- Project connection and PR run (destinations): Projects and PR runs (the glossary term for the run list).
- Schedule configuration and Schedule job (destinations): Schedule configs and Schedule jobs.
- Connector and AI catalog (destinations): configuration links, alongside notification and system settings.
- Account and Machine key (administrative destinations): an Administration section with Account approval and Machine keys when the profile allows them.
- Service health (indicator): a periodic shallow health check reports Core Online or Offline.
- Theme preference (toggle): also accessible in the narrow header.

Decisions opens `UX-decision-inbox` from the project management navigation and highlights the current destination.

Active destination (every navigation link, administrative ones included; emphasis per `docs/steering/visual-style.md`):

- The active link carries `aria-current="page"`, semibold text, the neutral accent fill and a 1px ink outline (`sidebar-ring`, at least 3:1 against the sidebar and the fill in both themes), so it is identifiable without color. The left rule stays reserved for attention.
- When the sidebar list overflows, the active link is scrolled into view.
- Keyboard focus shows a translucent ink ring, distinct from the 1px active outline.

Pending-decision signal (attention, operator debt):

- Source: one read of the existing Decision inbox list (`GET /api/v1/pipeline-runs/decisions`, all visible projects, no filters, `limit=1`) on mount, once a minute while the tab is visible, when the tab becomes visible again, and on navigation at most once every 15 seconds. No other request is added.
- Count: rows that carry attention in `UX-decision-inbox` (actionable "Needs decision" and "Answer saved — resume pending"); "Answer publication pending" rows are not counted. The shell shows the list's exact `actionable_total_count` (`CAP-PR-operator-decisions`), never a lower bound; it counts inbox decisions only, not other operator-owed work.
- When the count is above zero: a 2px `attention-text` rule across the top bar (the desktop top bar and the narrow header), an `attention` Badge with the count on the Decisions link (accessible name "Decisions N pending decisions"), and on narrow displays an "N pending" Badge link to `UX-decision-inbox` in the header.
- Zero stays fully neutral: no rule, no Badge, no narrow-header link.
- Unknown (loading, a failed read and a response without a valid count) must not read as zero or as debt: a neutral `outline` Badge reading "?" on the Decisions link (accessible name "Decisions Pending decisions unknown", tooltip "Pending decisions unknown") and, on narrow displays, the same "?" Badge as a link to `UX-decision-inbox` in the header (accessible name "Decisions: Pending decisions unknown", same tooltip). No top rule and no attention color. A later successful read replaces the mark with the count or with nothing; a failed refresh after a known count also returns to unknown.

## 3. States

- **populated**: authenticated children and navigation remain usable; choose a destination or Logout.
- **menu-open**: narrow navigation is expanded; selecting another URL implicitly closes its route-bound menu state.
- **offline**: the health indicator changes without itself removing the session or navigation.
- **decisions-owed**: the pending-decision count is above zero; the top rule and count Badges appear. Open Decisions to act.
- **decisions-neutral**: the count is zero; the shell shows no mark at all.
- **decisions-unknown**: the count is loading, failed or invalid; the shell shows the neutral "?" mark with no attention. Open Decisions to see the list directly.
- **sign-out-error**: a failed logout produces a toast; the operator can retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Decisions | global: navigate to pending operator work | populated, decisions-owed, decisions-neutral, decisions-unknown | populated | `UX-decision-inbox` | | The cross-project worklist opens. |
| Pending count Badge link (narrow header) | global: navigate to pending operator work | decisions-owed | populated | `UX-decision-inbox` | | The cross-project worklist opens. |
| Unknown "?" Badge link (narrow header) | global: navigate to pending operator work | decisions-unknown | populated | `UX-decision-inbox` | | The cross-project worklist opens and shows its own loading or error state. |
| Count check (mount, minute, tab visible, throttled navigation) | global: keep the shell signal current | decisions-owed, decisions-neutral, decisions-unknown | decisions-owed, decisions-neutral, decisions-unknown | | `CAP-PR-operator-decisions` | The rule and Badges follow the new count; failures fall back to the neutral "?" mark. |
| Display the admitted console | `UC-access-hub` 2, `UC-access-hub` 3 | populated | populated |  | `CAP-ACCESS-authentication-authorization` | The requested feature screen is rendered inside the shell. |
| Logout | `UC-access-hub` 5 | populated | populated | `UX-sign-in` | `CAP-ACCESS-authentication-authorization` | Successful logout replaces the shell with the sign-in screen; failure is a toast. |
| Open Dashboard | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | System Overview becomes the selected screen. |
| Open Projects | global: navigation between management surfaces | populated | populated | `UX-projects` |  | The project list becomes the selected screen. |
| Open PR runs | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | The run list becomes the selected screen. |
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

Implementation inspected: `modules/hub-ui/src/lib/components/shared/AppShell.svelte`, `modules/hub-ui/src/lib/components/shared/SidebarLink.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/pending-decisions.svelte.ts` and `modules/hub-ui/src/routes/+layout.svelte`. `AppShell.integration.test.ts` covers the active outline on primary and administrative links, the one-row request, the "PR runs" label and the owed, exact backlog, zero (no mark) and unknown (error, failure, invalid count and loading: neutral "?" with its accessible label and tooltip, no rule) count states; `pending-decisions.test.ts` covers the count rules, including invalid counts and the unknown predicate; `layout-contrast.test.ts` checks the sidebar text and outline pairs in both themes. Session behavior is covered by the inspected `modules/hub-ui/src/lib/api/client.test.ts` and `modules/hub-ui/src/lib/stores/session.test.ts`.
