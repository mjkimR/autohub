---
id: UX-projects
title: Projects
summary: "Select a project connection and inspect its repository, revision, enabled state and recorded access check before opening project work."
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
- **Facts to commit**: project name, type, revision, GitHub repository, workflow, enabled state and saved check badge.
- **Secondary items**: configuration, checking and scheduling open their own modals.

## 2. Content

The Project connection table is primary. Search and refresh sit above it; pagination follows the table. Quick actions stay with their row.

- Project connection (table row): name opens `UX-project-detail`; revision and repository identify the saved connection.
  - Recorded access check (badge): `Access OK`, `Issue` or `Unchecked`; this is not provider execution evidence.
  - Quick actions: `UX-project-settings`, `UX-connection-test-check`, `UX-project-schedule`, `UX-agent-schedules` and deletion.
- Project connection (creation form): `UX-project-create`.

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
| Configure Project | global: edit a selected project connection | populated | populated | `UX-project-settings` | `CAP-PROJ-project-connections` | Current settings populate the dialog. |
| Connection Check | global: inspect the selected saved access check | populated | populated | `UX-connection-test-check` | `CAP-PROJ-project-connections` | The saved result and check controls open. |
| Create Schedule | global: open project automation configuration | populated | populated | `UX-project-schedule` | `CAP-EXEC-scheduling-maintenance` | The schedule creation dialog opens. |
| Agent Schedules | global: configure provider-session schedules | populated | populated | `UX-agent-schedules` | `CAP-AGENT-provider-sessions` | The agent schedules dialog opens. |
| Delete Project and confirm | global: remove a project when retained-reference checks permit it | populated | populated, empty |  | `CAP-PROJ-project-connections` | Browser confirmation precedes deletion; a toast reports success or refusal. |
| Refresh / search / change page | global: find and reload project connections | populated, empty, error | loading |  | `CAP-PROJ-project-connections` | The list reloads and reports a load error when unavailable. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
