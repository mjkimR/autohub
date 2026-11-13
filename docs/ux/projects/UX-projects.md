---
id: UX-projects
title: Projects
summary: "Select a project connection and inspect its repository, revision, enabled state, recorded access check and Needs-you count, then open the project, its exception strip or its Automation or Settings section."
area: projects
element: screen
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
  - CAP-PR-owed-items
---

# [UX-projects] Projects

## 1. Purpose

- **Primary task**: select a Project connection.
- **Facts to commit**: project name, type, revision, GitHub repository, workflow, enabled state, saved access check
  and how many owed items wait for the operator in each project.
- **Secondary items**: configuration has one home, the project's Setup sections in `UX-project-detail`; a row links
  there instead of opening an edit dialog. Creation and the access check open their own modals.

## 2. Content

The Project connection table is primary. Search and refresh sit above it; pagination follows the table.

- Project connection (table row): name opens `UX-project-detail`; revision and repository identify the saved
  connection.
  - Recorded access check (badge button): `Access OK`, `Issue` or `Unchecked`; it opens `UX-connection-test-check`.
    This is not provider execution evidence.
  - Needs you (count link): the project's counted owed items (`CAP-PR-owed-items` `by_project`) on an `attention`
    Badge with a dot; it opens the project's exception strip in `UX-project-detail` (`?tab=overview#needs-you`).
    A project with nothing owed shows nothing, never `0`. While the counts are loading or after a failed read the
    cell shows a neutral `—`; a failed read names its reason in the tooltip. Failed runs are not counted. The row
    never takes an attention fill (`docs/steering/visual-style.md`).
  - Row links: `Automation` and `Settings` open those Setup sections of `UX-project-detail`.
- Project connection (creation form): `UX-project-create`.

Below the `md` breakpoint the providers column is hidden and the repository is shown under the name; below `sm` the
Needs-you, status and row-link columns are hidden as well: the status badge (`Active` or `Disabled`, with its icon)
and the Needs-you count move under the name, and the name opens the project.

The list reads `GET /api/v1/owed-items/counts` once per list load, never once per row: on opening the screen, on
Refresh, after creating a project and after an access check. Search and paging reuse the counts they already have.

The route is `/projects`.

## 3. States

- **populated**: inspect rows, search, change page or open a project.
- **empty**: `No projects found`; change the search or create a project.
- **loading**: table loading message; refresh is disabled while loading.
- **error**: load error and unavailable table; Retry requests the list again.
- **counts unknown**: the Needs-you cells show a neutral `—` while counts load or after the counts read fails; the
  list itself stays usable.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Inspect saved row | `UC-configure-project-connection` 4 | populated | populated | | `CAP-PROJ-project-connections` | Saved repository, revision and access-check status identify the current configuration. |
| Open project name | global: navigate to the selected project | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | Project detail opens. |
| New Project | global: create the project shell before configuring a connection | populated, empty | populated | `UX-project-create` | `CAP-PROJ-project-connections` | Name and project-type form opens. |
| Automation / Settings link | global: edit a project in its Setup sections | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The selected section of the project opens (`?tab=automation` or `?tab=settings`). |
| Needs-you count | global: find the projects whose work waits for the operator | populated | populated | `UX-project-detail` | `CAP-PR-owed-items` | The project opens at its exception strip, which breaks the count down by kind. |
| Access check badge | global: inspect the selected saved access check | populated | populated | `UX-connection-test-check` | `CAP-PROJ-project-connections` | The saved result and check controls open. |
| Refresh / search / change page | global: find and reload project connections | populated, empty, error | loading |  | `CAP-PROJ-project-connections`, `CAP-PR-owed-items` | The list reloads and reports a load error when unavailable; Refresh also re-reads the Needs-you counts. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/owed-signals.ts`

Inspected check: `ProjectsView.integration.test.ts` asserts the Automation and Settings link targets and that the
list offers no configure, schedule, agent-schedule or delete action. It also asserts the Needs-you column for
populated, zero, unknown (loading) and failed counts, its link target, and one counts read per load that search reuses
and Refresh repeats. The content and transitions are derived from
source inspection. This document does not assert a browser walkthrough or live GitHub/provider verification.
