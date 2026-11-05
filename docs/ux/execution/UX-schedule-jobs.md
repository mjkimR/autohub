---
id: UX-schedule-jobs
title: Schedule job history screen
summary: "Inspect paginated scheduler execution outcomes with search and status filtering, without retrying or mutating individual jobs."
area: execution
element: screen
status: active
usecases: []
capabilities:
  - CAP-EXEC-scheduling-maintenance
---

# [UX-schedule-jobs] Schedule job history screen

## 1. Purpose

- **Primary task**: inspect recorded Schedule job outcomes.
- **Facts to commit**: job name/status, error detail when present, start/finish times and dispatcher correlation.
- **Secondary items**: filters and paging change the observed slice; the console supplies navigation to configuration and other execution owners.

## 2. Content

The execution-history table is primary at `/schedules/jobs`; search, status filter and Refresh precede it.

- Schedule job (table row): name, status badge, optional error message, start time, optional finish time and dispatcher run ID or manual.
- Schedule job (status filter): All statuses, Pending, Success or Failure.
- Schedule job (search and page controls): text search and counted pagination; rows use a narrow-display stacked presentation.

## 3. States

- **loading**: Loading job runs replaces table content; await the result.
- **populated**: inspect rows or refine the requested slice.
- **empty**: No execution logs recorded remains with filtering and navigation available.
- **error**: LoadError offers Retry and the table says List unavailable; pagination is hidden for that failed load.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or Retry | global: inspect operational state without starting the underlying work | populated | loading |  | `CAP-EXEC-scheduling-maintenance` | The current slice reloads or presents an explicit failure. |
| Search, change status or paginate | global: inspect operational state without starting the underlying work | populated | loading |  | `CAP-EXEC-scheduling-maintenance` | The requested slice replaces the table; filter changes return to the first page. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-schedule-configs` |  | Schedule administration or another chosen screen appears. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/scheduling/schedule-jobs/ScheduleJobsView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/scheduling/schedule-jobs/ScheduleJobsView.integration.test.ts`.
