---
id: UX-dashboard
title: System health screen
summary: "Summarize service health, scheduler heartbeat and delivery activity under System › Health, with navigation to the corresponding management screens; operator-owed work lives on the Attention landing."
area: operations
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
  - CAP-PR-pull-request-delivery
  - CAP-NOTIFY-operator-notifications
---

# [UX-dashboard] System health screen

## 1. Purpose

- **Primary task**: assess installation health and choose the next operational surface.
- **Facts to commit**: API/database health, scheduler trigger state and last tick, PR run counts and recent activity.
- **Secondary items**: metric cards and recent lists navigate to the owning screens; what waits for the operator is on `UX-attention`; `UX-app-shell` supplies global session controls.

## 2. Content

At `/system/health` (System › Health; the console root `/` is `UX-attention`), the title "System health" and a subtitle linking to Attention lead; health indicators precede the primary PR run summary; supporting object counts and recent activity follow. Metric values use an unknown marker when statistics cannot be loaded.

- Service health (status summary): API and database indicators, plus scheduler-trigger Firing, Stopped, Never fired or Unknown and the last recorded tick. The trigger heartbeat is distinct from the protected System maintenance schedule.
- PR run (summary counts): Total Runs, Active Work, Awaiting CI, Completed and Held or failed as neutral counts of equal weight. Held or failed sums failed, paused and blocked PR runs as a run-state statistic; its caption lists the non-zero states in the order failed, paused, blocked (for example "1 failed · 2 paused · 1 blocked") or reads "Failed, paused, or blocked". No tile carries attention and none links to a filtered list. This screen shows no owed count: it already appears in the shell Badge and as the summary of `UX-attention`, a second copy here would duplicate that surface, and reading `GET /api/v1/owed-items/counts` on this screen's 5–30 second polling would add a database read per refresh against the shared connection budget.
- Project connection, Schedule configuration and Connector (metric cards): aggregate counts that lead to their management screens.
- PR run (recent list "Recent PR runs"): PR identity/title (opens `UX-run-page`), branch, state as the PR run state badge (label plus icon, emphasis by role per `docs/steering/visual-style.md`) and external PR link when available.
- Schedule job (recent list): recent execution outcomes.
- Refresh controls: manual Refresh and Off/5s/15s/30s polling, with the last fully successful refresh time. The live-refresh indicator shows an icon and text without motion.

## 3. States

- **loading**: Refresh is busy and statistics use an unknown marker on neutral tiles. API/database indicators initially show Unavailable/Disconnected until their independent checks resolve.
- **populated**: inspect aggregates and follow a metric/list navigation control; no tile carries attention.
- **empty**: recent lists explain that no runs or jobs are recorded; navigation remains available.
- **degraded**: failed sections show unavailable/unknown indicators; a load warning offers Retry while successful or retained lists remain visible.
- **polling-off**: automatic refresh is stopped; manual Refresh remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or Retry | global: inspect operational state without starting the underlying work | populated | loading |  |  | Independent health/statistics/list requests update their own regions. |
| Choose Off, 5s, 15s or 30s | global: inspect operational state without starting the underlying work | populated | populated |  |  | The polling choice changes; it does not dispatch work. |
| Open a project metric or project navigation | global: navigation between management surfaces | populated | populated | `UX-projects` |  | Project connections are listed. |
| Open Attention (subtitle link) | global: navigation to what waits for the operator | populated | populated | `UX-attention` |  | The Attention landing opens. |
| View All Runs | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | PR runs are listed. |
| Open a recent PR run | global: inspect one recent PR run in its home | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The PR run page opens. |
| Open the schedule metric | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule configurations are listed. |
| Open execution history | global: navigation between management surfaces | populated | populated | `UX-schedule-jobs` |  | Schedule jobs are listed. |
| Open connector metric | global: navigation between management surfaces | populated | populated | `UX-connectors` |  | Connector configuration is shown. |
| View PR | global: inspect operational state without starting the underlying work | populated | populated | end |  | The external GitHub PR opens in another tab. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/dashboard/DashboardView.svelte`, `modules/hub-ui/src/lib/features/dashboard/DashboardHealth.svelte` and `modules/hub-ui/src/lib/features/dashboard/dashboard.svelte.ts`. Route: `modules/hub-ui/src/routes/system/health/+page.svelte`. Inspected check: `modules/hub-ui/src/lib/features/dashboard/DashboardView.integration.test.ts` (run-state counts, the neutral Held-or-failed tile with its breakdown and no attention or owed read, the title and the Attention link).
