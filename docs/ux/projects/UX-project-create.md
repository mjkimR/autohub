---
id: UX-project-create
title: Create Project
summary: "Create a named project shell and select its general or SDD type before configuring its repository connection."
area: projects
element: modal
status: active
usecases:
  []
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-project-create] Create Project

## 1. Purpose

- **Primary task**: create a Project connection shell.
- **Facts to commit**: name and `general` or `sdd` project type.
- **Secondary items**: repository, credentials and automation are configured after creation.

## 2. Content

The name and project-type controls form the primary region; Cancel and Create Project follow them.

- Project connection (new-project form): name and project type; creation enables the project.
- Project connection (saved list row): appears in `UX-projects` after success.

## 3. States

- **populated**: enter a name, choose the type, submit or cancel.
- **loading**: `Creating...` disables duplicate submission.
- **error**: validation or request failure appears as a toast; correct the name or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Create Project | global: create an initially unconnected project shell | populated | loading | close | `CAP-PROJ-project-connections` | Success toast closes the dialog and reloads the projects list; failure keeps the form. |
| Cancel / dismiss | global: leave the creation form | populated, error | populated | close |  | The project list remains available. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
