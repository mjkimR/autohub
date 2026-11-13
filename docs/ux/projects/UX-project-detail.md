---
id: UX-project-detail
title: Project Detail
summary: "Inspect one project connection and navigate between its repository, work plans, PR runs, connections, automation and settings."
area: projects
element: screen
status: active
usecases:
  []
capabilities:
  - CAP-PROJ-project-connections
  - CAP-CONN-connection-verification
  - CAP-WORK-work-plan-execution
  - CAP-PR-pull-request-delivery
  - CAP-DOC-repository-viewer
---

# [UX-project-detail] Project Detail

## 1. Purpose

- **Primary task**: choose the next action for one Project connection.
- **Facts to commit**: project identity, repository, project type and enabled state.
- **Secondary items**: tab content isolates repository inspection, execution, connection setup and configuration.

## 2. Content

The project header anchors all tabs. Overview is the entry region; each selected tab replaces the task region below the navigation.

- Project connection (header and overview): repository link, enabled/type badges, automatic-merge setting and saved access status.
  - Connection test (latest-per-catalog summary): verified, failure or retest recommendation.
  - PR run (recent row): PR, branch and the PR run state badge; opens `UX-run-page`.
- Repository viewer (tab): `UX-repository`.
- Work Plan (tab): `UX-work-plans`.
- PR run (tab): `UX-pipeline-runs` scoped to this project.
- Project connection (connection tab): `UX-project-connections`.
- Project connection (automation/settings tabs): automation policy, schedules and general settings; schedule controls open `UX-agent-schedules` or `UX-project-schedule`.

The route is `/projects/{projectId}` and the selected section is the `tab` query parameter. A PR run of the project has its own page at `/projects/{projectId}/runs/{runId}` (`UX-run-page`).

## 3. States

- **populated**: change tabs, inspect activity, edit the relevant form or return to Projects.
- **loading**: project loading text; wait for its identity and options.
- **error**: a project/load error offers Retry; the Projects backlink remains available.
- **empty**: the overview can have no development runs or verified connections; use Connections or Runs to proceed.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Projects backlink | global: return to project selection | populated, loading, error | populated | `UX-projects` | `CAP-PROJ-project-connections` | The projects list opens. |
| Repository tab | global: inspect repository documents | populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | The branch-specific repository viewer opens. |
| Plans tab | global: inspect pre-PR work | populated | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Project Work Plans open. |
| Runs tab | global: inspect project PR delivery | populated | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | The project run list opens; an old `run` link redirects to `UX-run-page`. |
| Recent run | global: open one PR run from the project overview | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run page opens. |
| Connections tab / connection overview card | global: inspect and configure project connections | populated | populated | `UX-project-connections` | `CAP-PROJ-project-connections`, `CAP-CONN-connection-verification` | Connection forms and isolated test history open. |
| Automation / settings tab | global: edit the relevant project configuration | populated | populated |  | `CAP-PROJ-project-connections` | The relevant settings form is shown. |
| Agent schedules | global: configure provider-session schedules | populated | populated | `UX-agent-schedules` | `CAP-AGENT-provider-sessions` | The agent schedules dialog opens. |
| Create CI observation schedule | global: configure project automation schedules | populated | populated | `UX-project-schedule` | `CAP-EXEC-scheduling-maintenance` | The schedule creation dialog opens. |
| Delete project and confirm | global: remove a project if its retained history permits deletion | populated | loading | `UX-projects` | `CAP-PROJ-project-connections` | Confirmation precedes the request; success navigates to Projects and failure produces a toast. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectDetailView.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectOverview.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
