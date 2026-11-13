---
id: UX-dashboard
title: System overview screen
summary: "Summarize service health, scheduler heartbeat and delivery activity, with navigation to the corresponding management screens."
area: operations
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
  - CAP-PR-pull-request-delivery
  - CAP-NOTIFY-operator-notifications
---

# [UX-dashboard] System overview screen

## 1. Purpose

- **Primary task**: assess installation health and choose the next operational surface.
- **Facts to commit**: API/database health, scheduler trigger state and last tick, PR run counts and recent activity.
- **Secondary items**: metric cards and recent lists navigate to the owning screens; `UX-app-shell` supplies global session controls.

## 2. Content

At `/`, health indicators precede the primary PR run summary; supporting object counts and recent activity follow. Metric values use an unknown marker when statistics cannot be loaded.

- Service health (status summary): API and database indicators, plus scheduler-trigger Firing, Stopped, Never fired or Unknown and the last recorded tick. The trigger heartbeat is distinct from the protected System maintenance schedule.
- PR run (summary counts): Total Runs, Active Work, Awaiting CI and Completed as neutral counts of equal weight, and a Needs-you count of failed, paused or blocked PR runs. The tile switches to the owed count of `CAP-PR-owed-items` together with the shell Badge; today it keeps the run-state sum. The Needs-you tile is the only emphasized tile:
  - above zero: attention emphasis, the count, a per-state breakdown caption of the non-zero counts in the order failed, paused, blocked (for example "1 failed · 2 paused · 1 blocked"), and a link to `UX-pipeline-runs`;
  - zero: neutral, "No failed or held runs", caption "Failed, paused, or blocked", not a link;
  - statistics unavailable: neutral, the unknown marker, the same caption, not a link.
- Project connection, Schedule configuration and Connector (metric cards): aggregate counts that lead to their management screens.
- PR run (recent list "Recent PR runs"): PR identity/title (opens `UX-run-page`), branch, state as the PR run state badge (label plus icon, emphasis by role per `docs/steering/visual-style.md`) and external PR link when available.
- Schedule job (recent list): recent execution outcomes.
- Refresh controls: manual Refresh and Off/5s/15s/30s polling, with the last fully successful refresh time. The live-refresh indicator shows an icon and text without motion.

## 3. States

- **loading**: Refresh is busy and statistics use an unknown marker on neutral tiles. API/database indicators initially show Unavailable/Disconnected until their independent checks resolve.
- **populated**: inspect aggregates and follow a metric/list navigation control; the Needs-you tile carries attention emphasis only while its count is above zero.
- **empty**: recent lists explain that no runs or jobs are recorded; navigation remains available.
- **degraded**: failed sections show unavailable/unknown indicators (the Needs-you tile stays neutral and is not a link); a load warning offers Retry while successful or retained lists remain visible.
- **polling-off**: automatic refresh is stopped; manual Refresh remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or Retry | global: inspect operational state without starting the underlying work | populated | loading |  |  | Independent health/statistics/list requests update their own regions. |
| Choose Off, 5s, 15s or 30s | global: inspect operational state without starting the underlying work | populated | populated |  |  | The polling choice changes; it does not dispatch work. |
| Open a project metric or project navigation | global: navigation between management surfaces | populated | populated | `UX-projects` |  | Project connections are listed. |
| Open the Needs-you tile | global: navigation from the exception count to the runs it counts | populated | populated | `UX-pipeline-runs` |  | PR runs opens with default filters; the operator filters by state and continues on a run's page with Resume (`UC-deliver-pull-request` *c), Cancel run (`UC-deliver-pull-request` *b) or Decisions for a blocked run's question. |
| View All Runs | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | PR runs are listed. |
| Open a recent PR run | global: inspect one recent PR run in its home | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The PR run page opens. |
| Open the schedule metric | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule configurations are listed. |
| Open execution history | global: navigation between management surfaces | populated | populated | `UX-schedule-jobs` |  | Schedule jobs are listed. |
| Open connector metric | global: navigation between management surfaces | populated | populated | `UX-connectors` |  | Connector configuration is shown. |
| View PR | global: inspect operational state without starting the underlying work | populated | populated | end |  | The external GitHub PR opens in another tab. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/dashboard/DashboardView.svelte`, `modules/hub-ui/src/lib/features/dashboard/DashboardHealth.svelte` and `modules/hub-ui/src/lib/features/dashboard/dashboard.svelte.ts`. Inspected check: `modules/hub-ui/src/lib/features/dashboard/DashboardView.integration.test.ts`.
