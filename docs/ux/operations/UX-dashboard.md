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
- PR run (summary counts): total, active implementation, awaiting CI, completed and stopped/error counts.
- Project connection, Schedule configuration and Connector (metric cards): aggregate counts that lead to their management screens.
- PR run (recent list): PR identity/title, branch, state and external PR link when available.
- Schedule job (recent list): recent execution outcomes.
- Refresh controls: manual Refresh and Off/5s/15s/30s polling, with the last fully successful refresh time.

## 3. States

- **loading**: Refresh is busy and statistics use an unknown marker. API/database indicators initially show Unavailable/Disconnected until their independent checks resolve.
- **populated**: inspect aggregates and follow a metric/list navigation control.
- **empty**: recent lists explain that no runs or jobs are recorded; navigation remains available.
- **degraded**: failed sections show unavailable/unknown indicators; a load warning offers Retry while successful or retained lists remain visible.
- **polling-off**: automatic refresh is stopped; manual Refresh remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or Retry | global: inspect operational state without starting the underlying work | populated | loading |  |  | Independent health/statistics/list requests update their own regions. |
| Choose Off, 5s, 15s or 30s | global: inspect operational state without starting the underlying work | populated | populated |  |  | The polling choice changes; it does not dispatch work. |
| Open a project metric or project navigation | global: navigation between management surfaces | populated | populated | `UX-projects` |  | Project connections are listed. |
| View All Runs or open run navigation | global: navigation between management surfaces | populated | populated | `UX-pipeline-runs` |  | PR runs are listed. |
| Open the schedule metric | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule configurations are listed. |
| Open execution history | global: navigation between management surfaces | populated | populated | `UX-schedule-jobs` |  | Schedule jobs are listed. |
| Open connector metric | global: navigation between management surfaces | populated | populated | `UX-connectors` |  | Connector configuration is shown. |
| View PR | global: inspect operational state without starting the underlying work | populated | populated | end |  | The external GitHub PR opens in another tab. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/dashboard/DashboardView.svelte`, `modules/hub-ui/src/lib/features/dashboard/DashboardHealth.svelte` and `modules/hub-ui/src/lib/features/dashboard/dashboard.svelte.ts`. Inspected check: `modules/hub-ui/src/lib/features/dashboard/DashboardView.integration.test.ts`.
