---
id: UX-app-shell
title: Authenticated navigation panel
summary: "Provide navigation grouped by operator job, health indication and session controls around each authenticated management screen, and signal the owed-item count from any screen with a link to the Attention landing."
area: navigation
element: panel
status: active
usecases:
  - UC-access-hub
capabilities:
  - CAP-ACCESS-authentication-authorization
  - CAP-PR-operator-decisions
  - CAP-PR-owed-items
---

# [UX-app-shell] Authenticated navigation panel

## 1. Purpose

- **Primary task**: navigate the management console within an admitted Browser session.
- **Facts to commit**: the active destination, API-session status, Core Online/Offline indicator and, while any are owed, the owed-item count ("Needs you"); while the count is unknown, a neutral mark that says so.
- **Secondary items**: diagnostic destinations sit in a collapsed System group; administrative links appear after the profile identifies a superadministrator; feature content stays in the selected screen.

## 2. Content

The navigation is secondary to the active screen. It is a persistent side region on wide displays and a Menu-controlled region on narrow displays.

- Browser session (status badge): Active and Logout.
- Browser session (navigation context): current route label and active link.
- Navigation groups, in order, grouped by operator job (one link per routed list screen):
  - **Attention**: Attention (`/`, `UX-attention`) with the owed-item signal, and Decisions (`UX-decision-inbox`), the decision-kind view, with its decision count.
  - **Work**: Projects and PR runs (Project connection and PR run; "PR runs" is the glossary term for the run list).
  - **Setup**: Connectors, AI catalogs and Notifications (Connector, AI catalog and notification channel configuration).
  - **System** (diagnostics, collapsible): Health (`/system/health`, `UX-dashboard`), Schedule configs, Schedule jobs, Webhook deliveries, Task specs and System configs.
  - **Administration**: Account approval and Machine keys (Account and Machine key), only when the profile allows them.
- Service health (indicator): a periodic shallow health check reports Core Online or Offline.
- Theme preference (toggle): also accessible in the narrow header.

Attention opens `UX-attention` and Decisions opens `UX-decision-inbox`; the current destination is highlighted.

System group (collapse behavior):

- The group label is a disclosure button ("System" with a chevron) carrying `aria-expanded` and `aria-controls` for its link list; Enter and Space toggle it, and a collapsed list is hidden from the accessibility tree and the tab order.
- Default: collapsed. The last toggle is remembered for this browser (`localStorage` key `autohub.nav.system.open`); when storage is unavailable or blocked the group falls back to collapsed and still toggles for the session.
- Auto-expand: when the current route is one of its destinations the group opens regardless of the remembered state, so the active link stays visible.
- A toggle on the current page overrides auto-expand until the operator navigates. If the operator collapses the group while it holds the current page, the button text turns ink and shows a small ink dot with the accessible suffix ", contains the current page".
- The narrow Menu shows the same groups with the same behavior; the toggle keeps a 44px target there and the heading rhythm of the static group labels.

Current route label (the desktop top bar and the narrow header):

- A navigation destination shows its link label. Routes without their own link name the object and highlight the list that owns them: a project (`/projects/[projectId]`) reads "Project" under Projects, a PR run page (`/projects/[projectId]/runs/[runId]`) reads "PR run" under Projects (matching its breadcrumb), and the run redirect (`/runs/[runId]`) reads "PR run" under PR runs.
- Any other route is the not-found page and reads "Page not found" with no active link.

Active destination (every navigation link, administrative ones included; emphasis per `docs/steering/visual-style.md`):

- The active link carries `aria-current="page"`, semibold text, the neutral accent fill and a 1px ink outline (`sidebar-ring`, at least 3:1 against the sidebar and the fill in both themes), so it is identifiable without color. The left rule stays reserved for attention.
- When the sidebar list overflows, the active link is scrolled into view.
- Keyboard focus shows a translucent ink ring, distinct from the 1px active outline.

Owed-item signal (attention, operator debt):

- Source: one read of the owed counts (`GET /api/v1/owed-items/counts`, all visible projects, `CAP-PR-owed-items`) on mount, once a minute while the tab is visible, when the tab becomes visible again, and on navigation at most once every 15 seconds. No other request is added; `UX-attention` reuses this response for its summary and group sizes.
- Count: the response's `total`, the counted owed items of every kind across projects. Failed PR runs are listed on `UX-attention` but never counted, so failures alone keep the shell neutral. The Decisions link shows `by_kind.decision` from the same response, which equals the inbox's `actionable_total_count` (`CAP-PR-owed-items` rule 4).
- When the total is above zero: a 2px `attention-text` rule across the top bar (the desktop top bar and the narrow header), an `attention` Badge with the total on the Attention link (accessible name "Attention N items need you"), and on narrow displays a "Needs you · N" Badge link to `UX-attention` in the header (accessible name "Attention: N items need you").
- Decisions count: while `by_kind.decision` is above zero, a neutral `secondary` Badge with that count on the Decisions link (accessible name "Decisions N pending decisions"). It carries no attention, because the Attention Badge already counts these decisions.
- Zero stays fully neutral: no rule, no Badge, no narrow-header link.
- Unknown (loading, a failed read and a response without a valid total) must not read as zero or as debt: a neutral `outline` Badge reading "?" on the Attention link (accessible name "Attention Owed items unknown", tooltip "Owed items unknown") and, on narrow displays, the same "?" Badge as a link to `UX-attention` in the header (accessible name "Attention: Owed items unknown", same tooltip). The Decisions link shows no count. No top rule and no attention color. A later successful read replaces the mark with the count or with nothing; a failed refresh after a known count also returns to unknown.

## 3. States

- **populated**: authenticated children and navigation remain usable; choose a destination or Logout.
- **system-collapsed**: the System group shows only its toggle (default, and remembered after a collapse); on a System route the collapsed toggle carries the "contains the current page" mark.
- **system-expanded**: the System links are listed, because the operator opened the group or the current route is inside it.
- **menu-open**: narrow navigation is expanded; selecting another URL implicitly closes its route-bound menu state.
- **offline**: the health indicator changes without itself removing the session or navigation.
- **owed**: the owed-item total is above zero; the top rule and the Attention Badges appear. Open Attention to triage.
- **owed-neutral**: the total is zero; the shell shows no mark at all.
- **owed-unknown**: the count is loading, failed or invalid; the shell shows the neutral "?" mark with no attention. Open Attention to see the list directly.
- **sign-out-error**: a failed logout produces a toast; the operator can retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Attention | global: navigate to pending operator work | populated, owed, owed-neutral, owed-unknown | populated | `UX-attention` | | The cross-project owed list opens. |
| Decisions | global: navigate to pending operator decisions | populated, owed, owed-neutral, owed-unknown | populated | `UX-decision-inbox` | | The cross-project decision worklist opens. |
| "Needs you" Badge link (narrow header) | global: navigate to pending operator work | owed | populated | `UX-attention` | | The cross-project owed list opens. |
| Unknown "?" Badge link (narrow header) | global: navigate to pending operator work | owed-unknown | populated | `UX-attention` | | The owed list opens and shows its own loading or error state. |
| Count check (mount, minute, tab visible, throttled navigation) | global: keep the shell signal current | owed, owed-neutral, owed-unknown | owed, owed-neutral, owed-unknown | | `CAP-PR-owed-items` | The rule and Badges follow the new count; failures fall back to the neutral "?" mark. |
| Display the admitted console | `UC-access-hub` 2, `UC-access-hub` 3 | populated | populated |  | `CAP-ACCESS-authentication-authorization` | The requested feature screen is rendered inside the shell. |
| Logout | `UC-access-hub` 5 | populated | populated | `UX-sign-in` | `CAP-ACCESS-authentication-authorization` | Successful logout replaces the shell with the sign-in screen; failure is a toast. |
| Open Health | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | System health becomes the selected screen. |
| Open Projects | global: navigation between management surfaces | populated | populated | `UX-projects` |  | The project list becomes the selected screen. |
| Open PR runs | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | The run list becomes the selected screen. |
| Open Schedule configs | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule configurations appear. |
| Open Schedule jobs | global: navigation between management surfaces | populated | populated | `UX-schedule-jobs` |  | Schedule-job history appears. |
| Open Connectors | global: navigation between management surfaces | populated | populated | `UX-connectors` |  | Connector configuration appears. |
| Open AI catalogs | global: navigation between management surfaces | populated | populated | `UX-ai-catalogs` |  | AI catalog configuration appears. |
| Open Notifications | global: navigation between management surfaces | populated | populated | `UX-notifications` |  | Notification channels appear. |
| Open System configs | global: navigation between management surfaces | populated | populated | `UX-system-settings` |  | Read-only configuration records appear. |
| Open Task specs | global: navigation between management surfaces | populated | populated | `UX-task-specs` |  | Registered task specifications appear. |
| Open Webhook deliveries | global: navigation between management surfaces | populated | populated | `UX-webhook-deliveries` |  | Webhook delivery history appears. |
| Open Account approval | global: navigation between management surfaces | populated | populated | `UX-users` | `CAP-ACCESS-authentication-authorization` | The account table appears. |
| Open Machine keys | global: navigation between management surfaces | populated | populated | `UX-machines` | `CAP-ACCESS-authentication-authorization` | Machine administration appears. |
| Toggle System | global: reveal diagnostic destinations | system-collapsed, system-expanded | system-expanded, system-collapsed |  |  | The chevron rotates, aria-expanded follows and the choice is remembered for this browser. |
| Toggle Menu | global: reveal navigation on narrow displays | populated | menu-open |  |  | Menu expansion is reflected by aria-expanded. |
| Toggle theme | global: a console-wide visual preference | populated | populated |  |  | The theme changes without changing the current task. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/components/shared/AppShell.svelte`, `modules/hub-ui/src/lib/components/shared/app-shell-nav.ts` (groups, route ownership and labels, remembered group state), `modules/hub-ui/src/lib/components/shared/SidebarNavGroup.svelte`, `modules/hub-ui/src/lib/components/shared/SidebarLink.svelte`, `modules/hub-ui/src/lib/features/attention/owed-counts.svelte.ts` and `modules/hub-ui/src/routes/+layout.svelte`. `AppShell.integration.test.ts` covers the group order and membership, System collapsed by default with `aria-expanded`/`aria-controls`, auto-expansion and the active link on a System route, the "contains the current page" mark after collapsing there, the remembered open state and the blocked-storage fallback, the top-bar label and active link for run, project, setup and unknown routes, the active outline on primary and administrative links, the single counts read with no decision-inbox read, the Attention Badge and narrow "Needs you" link to `/`, the neutral decision count from the same response, the "PR runs" label and the owed, exact backlog, singular, failed-only zero (no mark) and unknown (error, failure, invalid and negative count and loading: neutral "?" with its accessible label and tooltip, no rule) count states; `app-shell-nav.test.ts` checks that every routed list screen has exactly one link, that only System collapses, the route-to-label map and the storage round trip; `owed-counts.test.ts` covers the count rules, including invalid totals, dropped invalid per-kind values and the phrases; `layout-contrast.test.ts` checks the sidebar text and outline pairs in both themes. Session behavior is covered by the inspected `modules/hub-ui/src/lib/api/client.test.ts` and `modules/hub-ui/src/lib/stores/session.test.ts`.
