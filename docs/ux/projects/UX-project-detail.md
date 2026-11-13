---
id: UX-project-detail
title: Project Detail
summary: "Inspect one project connection and what it owes the operator, and move between its Work sections (overview, PR runs, Work Plans, repository) and Setup sections (connections, automation with every owned schedule, settings)."
area: projects
element: screen
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
  - CAP-CONN-connection-verification
  - CAP-WORK-work-plan-execution
  - CAP-PR-pull-request-delivery
  - CAP-PR-ci-observation
  - CAP-DOC-repository-viewer
  - CAP-EXEC-scheduling-maintenance
  - CAP-AGENT-provider-sessions
  - CAP-PR-owed-items
---

# [UX-project-detail] Project Detail

## 1. Purpose

- **Primary task**: choose the next action for one Project connection.
- **Facts to commit**: project identity, repository, project type, enabled state and the owed items waiting in it.
- **Secondary items**: each section isolates one concern. Work sections show what the project is doing; Setup
  sections hold its configuration and are the only place a project is edited.

## 2. Content

A breadcrumb (`Projects` › project name) and the project header anchor every section. The section navigation below
the header groups the sections into **Work** and **Setup**; the selected section replaces the task region below it.
On a narrow screen the two groups stack as two rows.

- Project connection (header): name, `SDD` type badge, Active/Disabled status badge, repository and its GitHub link.
- Owed item (exception strip, `#needs-you`, under the header on every section): the project's owed items by kind,
  read with one `GET /api/v1/owed-items/counts?project_id=` (`CAP-PR-owed-items`). Each counted kind is an `attention`
  chip with a dot that opens the section where it is resolved:

  | Kind | Chip | Opens |
  | --- | --- | --- |
  | `decision` | `2 decisions` | Runs (`?tab=runs`), where held runs carry their question or approval |
  | `stopped-run` | `1 held run` | Runs (`?tab=runs`) |
  | `work-plan-proposed` | `1 plan awaiting decision` | Plans (`?tab=plans`) |
  | `work-item-recovery` | `1 recovery to inspect` | Plans (`?tab=plans`) |
  | `work-item-replacement` | `1 replacement to accept` | Plans (`?tab=plans`) |
  | `work-item-attention` | `1 Work Item needs attention` | Plans (`?tab=plans`) |
  | `sdd-batch-attention` | `1 batch needs attention` | Repository (`?tab=repository`) |
  | `connection-test-cleanup` | `1 cleanup to review` | Connections (`?tab=connections`) |
  | `failed-run` | `1 failed run` | Runs (`?tab=runs`); a quiet outline chip without attention weight, never counted |

  `View in Attention` opens the Attention landing filtered to the project (`/?project=<projectId>`) when a counted
  item exists. A clear project shows `No exceptions`; a project with only failed runs shows only their quiet chip.
- Work sections:
  - Overview (`overview`): automatic-merge setting, saved access status, latest connection test per catalog and
    recent PR runs; a recent run opens `UX-run-page`.
  - Runs (`runs`): `UX-pipeline-runs` scoped to this project.
  - Plans (`plans`): `UX-work-plans`.
  - Repository (`repository`): `UX-repository`.
- Setup sections:
  - Connections (`connections`): `UX-project-connections`.
  - Automation (`automation`), top to bottom:
    - Project connection (automation policy): the `UX-project-settings` automation region, including the dispatch
      interval.
    - Schedule configuration (owned schedules): every scheduler entry the project owns, grouped by owner kind.
      - Dispatch: the project's dispatch schedule with cadence, next run and status. It follows the dispatch interval
        and has no controls of its own. Without a GitHub connection the group explains that it appears once one is
        saved.
      - CI observation: each schedule with its observed PR numbers, cadence, next run (while active) and status, and
        Pause/Resume, Edit and Delete; New CI observation and Edit open `UX-project-schedule`.
      - Connection tests: scheduler entries left by connection tests started before system maintenance advanced them,
        shown read-only, and a link to the Connections section where tests are started, followed and cleaned up.
    - Schedule configuration (agent schedules): `UX-agent-schedules`, inline.
  - Settings (`settings`): the `UX-project-settings` general region and the delete zone.

The route is `/projects/{projectId}` and the selected section is the `tab` query parameter; grouping does not change
the parameter values, so existing links and notices keep their targets. A PR run of the project has its own page at
`/projects/{projectId}/runs/{runId}` (`UX-run-page`).

## 3. States

- **populated**: change sections, inspect activity, edit the relevant form or return to Projects. The exception
  strip shows one chip per owed kind, or `No exceptions` when the project owes nothing.
- **strip loading**: the strip shows static `Checking…` status text and no counts, never `0`.
- **strip error**: the strip shows a neutral `—` whose tooltip names the failed read; the rest of the page works.
- **loading**: project loading status text; wait for its identity and options.
- **error**: a project/load error offers Retry; a Projects backlink remains available. A failed owned-schedule load
  shows its own Retry inside the Automation section.
- **empty**: the overview can have no development runs or verified connections; use Connections or Runs to proceed.
  A project without a GitHub connection has no dispatch schedule and cannot create CI observation or agent
  schedules; the Automation section says to add the connection first.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Projects breadcrumb or backlink | global: return to project selection | populated, loading, error | populated | `UX-projects` | `CAP-PROJ-project-connections` | The projects list opens. |
| Decision chip | global: reach the project's runs held by a decision | populated | populated | `UX-pipeline-runs` | `CAP-PR-owed-items`, `CAP-PR-operator-decisions` | The project's Runs section opens; each held run shows its waiting question or approval. |
| Held run / failed run chip | global: find stopped or failed PR runs of the project | populated | populated | `UX-pipeline-runs` | `CAP-PR-owed-items`, `CAP-PR-pull-request-delivery` | The project's Runs section opens. |
| Plan, recovery, replacement or Work Item chip | global: find pre-PR work waiting for the operator | populated | populated | `UX-work-plans` | `CAP-PR-owed-items`, `CAP-WORK-work-plan-execution` | The project's Plans section opens. |
| Batch chip | global: reach the project's SDD batches in attention | populated | populated | `UX-repository` | `CAP-PR-owed-items`, `CAP-SDD-workflow-control` | The Repository section opens where retained batches are followed. |
| Cleanup chip | global: reach connection tests whose cleanup awaits review | populated | populated | `UX-project-connections` | `CAP-PR-owed-items`, `CAP-CONN-connection-verification` | The Connections section opens with connection test history and cleanup review. |
| View in Attention | global: see the project's owed items as a list | populated | populated | `UX-dashboard` | `CAP-PR-owed-items` | The landing route `/` opens with `?project=<projectId>`; once the Attention landing replaces the dashboard there, it lists only this project's owed items. |
| Change section or reload the project | global: keep the exception strip current without polling | populated | populated |  | `CAP-PR-owed-items` | The strip re-reads the counts once, keeping its last chips until the new counts arrive. |
| Repository section | global: inspect repository documents | populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | The branch-specific repository viewer opens. |
| Plans section | global: inspect pre-PR work | populated | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | Project Work Plans open. |
| Runs section | global: inspect project PR delivery | populated | populated | `UX-pipeline-runs` | `CAP-PR-pull-request-delivery` | The project run list opens; an old `run` link redirects to `UX-run-page`. |
| Recent run | global: open one PR run from the project overview | populated | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run page opens. |
| Connections section / connection overview card | global: open the project's connection setup | populated | populated | `UX-project-connections` | `CAP-PROJ-project-connections`, `CAP-CONN-connection-verification` | Connection forms and isolated test history open. |
| Automation section | `UC-configure-project-connection` 4 | populated | populated |  | `CAP-PROJ-project-connections` | The saved automation policy and the owned dispatch schedule it derives are shown with the other owned schedules. |
| Settings section | global: open the project's general settings | populated | populated |  | `CAP-PROJ-project-connections` | The general settings form and the delete zone are shown. |
| Pause or resume a CI observation schedule | global: maintain a project-owned scheduler entry at its owner | populated | populated |  | `CAP-EXEC-scheduling-maintenance` | A toast reports the change and the owned schedules reload; a refusal is toasted. |
| New CI observation / Edit | global: maintain a project-owned scheduler entry at its owner | populated | populated | `UX-project-schedule` | `CAP-EXEC-scheduling-maintenance`, `CAP-PR-ci-observation` | The CI observation dialog opens, empty or with the schedule. |
| Delete a CI observation schedule and confirm | global: maintain a project-owned scheduler entry at its owner | populated | populated |  | `CAP-EXEC-scheduling-maintenance` | Browser confirmation precedes deletion; a toast reports success or refusal. |
| Connections link (connection tests group) | global: manage connection tests where they run | populated | populated | `UX-connection-tests` | `CAP-CONN-connection-verification` | The Connections section opens. |
| Agent schedule actions | global: the inline `UX-agent-schedules` region carries its own use case steps | populated | populated | `UX-agent-schedules` | `CAP-AGENT-provider-sessions` | The inline agent schedules region handles the action. |
| Delete project and confirm | global: remove a project if its retained history permits deletion | populated | loading | `UX-projects` | `CAP-PROJ-project-connections` | Confirmation precedes the request; success navigates to Projects and failure produces a toast. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectDetailView.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectHeader.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectExceptionStrip.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/owed-signals.ts`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectSectionNav.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/project-tabs.ts`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectAutomation.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/OwnedSchedules.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/owned-schedules.ts`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectOverview.svelte`

Inspected check: `ProjectDetailView.integration.test.ts` covers the Work/Setup grouping and its `?tab=` URLs, the
breadcrumb, owned-schedule filtering by project, and pausing, editing, creating and deleting CI observation schedules
in the Automation section. `ProjectExceptionStrip.integration.test.ts` covers the strip's populated, clear,
failed-runs-only, loading and error states, the link of every kind, the `project` filter of `View in Attention`, one
counts read per load and one more per section change. Content and transitions are derived from source inspection and mocked-API screenshots;
this document does not assert live GitHub/provider verification.
