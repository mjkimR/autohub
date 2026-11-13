---
id: UX-projects
title: Projects
summary: "Select a project connection and inspect its repository, revision, enabled state and recorded access check, then open the project or its Automation or Settings section."
area: projects
element: screen
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-projects] Projects

## 1. Purpose

- **Primary task**: select a Project connection.
- **Facts to commit**: project name, type, revision, GitHub repository, workflow, enabled state and saved access check.
- **Secondary items**: configuration has one home, the project's Setup sections in `UX-project-detail`; a row links
  there instead of opening an edit dialog. Creation and the access check open their own modals.

## 2. Content

The Project connection table is primary. Search and refresh sit above it; pagination follows the table.

- Project connection (table row): name opens `UX-project-detail`; revision and repository identify the saved
  connection.
  - Recorded access check (badge button): `Access OK`, `Issue` or `Unchecked`; it opens `UX-connection-test-check`.
    This is not provider execution evidence.
  - Row links: `Automation` and `Settings` open those Setup sections of `UX-project-detail`.
- Project connection (creation form): `UX-project-create`.

Below the `md` breakpoint the providers column is hidden and the repository is shown under the name; below `sm` the
status and row-link columns are hidden as well: the status badge (`Active` or `Disabled`, with its icon) moves under
the name, and the name opens the project.

The route is `/projects`.

## 3. States

- **populated**: inspect rows, search, change page or open a project.
- **empty**: `No projects found`; change the search or create a project.
- **loading**: table loading message; refresh is disabled while loading.
- **error**: load error and unavailable table; Retry requests the list again.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Inspect saved row | `UC-configure-project-connection` 4 | populated | populated | | `CAP-PROJ-project-connections` | Saved repository, revision and access-check status identify the current configuration. |
| Open project name | global: navigate to the selected project | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | Project detail opens. |
| New Project | global: create the project shell before configuring a connection | populated, empty | populated | `UX-project-create` | `CAP-PROJ-project-connections` | Name and project-type form opens. |
| Automation / Settings link | global: edit a project in its Setup sections | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The selected section of the project opens (`?tab=automation` or `?tab=settings`). |
| Access check badge | global: inspect the selected saved access check | populated | populated | `UX-connection-test-check` | `CAP-PROJ-project-connections` | The saved result and check controls open. |
| Refresh / search / change page | global: find and reload project connections | populated, empty, error | loading |  | `CAP-PROJ-project-connections` | The list reloads and reports a load error when unavailable. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte`

Inspected check: `ProjectsView.integration.test.ts` asserts the Automation and Settings link targets and that the
list offers no configure, schedule, agent-schedule or delete action. The content and transitions are derived from
source inspection. This document does not assert a browser walkthrough or live GitHub/provider verification.
