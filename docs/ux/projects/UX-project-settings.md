---
id: UX-project-settings
title: Project Settings
summary: "Edit a project connection's general settings and automation policy in the project's Setup sections while preserving revision-checked saves."
area: projects
element: panel
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-project-settings] Project Settings

## 1. Purpose

- **Primary task**: update a Project connection.
- **Facts to commit**: current name, type, enabled state and automation policy.
- **Secondary items**: the form is shown only inside `UX-project-detail`, split into the Settings section (general
  region) and the Automation section (automation region); the Connections section edits the repository and
  verification fields (`UX-project-connections`). The Projects list links to these sections and has no edit dialog.

## 2. Content

Each region is one form with its own Save Changes.

- Project connection (general region, Settings section): name, type and enabled flag.
- Project connection (automation region, Automation section; shown only with a GitHub connection): merge after CI,
  merge method, dispatch interval, max runs in flight, AI catalog, CI and conflict fixing, `@auto-run` enrollment and
  "Adopt PRs opened by agent sessions", which explains that a provider session's PR becomes a PR run at CI
  observation. The region is a single column beside the owned schedules it drives; `UX-schedule-configs` links each
  project dispatch row to this region. Clearing max runs in flight saves no project limit.
- Save Changes: saves the loaded project revision and refreshes the project on success.

## 3. States

- **populated**: inspect or change the loaded values and save.
- **loading**: `Saving...` disables submission.
- **error**: a toast reports invalid input or a conflicting/stale request; the form keeps the input for correction or
  reloading through the project.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save Changes | `UC-configure-project-connection` 2, `UC-configure-project-connection` 3, `UC-configure-project-connection` 2a | populated | loading | | `CAP-PROJ-project-connections` | A success toast reloads the project and its sections; refusal leaves input available. |
| Save rejected configuration | `UC-configure-project-connection` 3a, `UC-configure-project-connection` 3b, `UC-configure-project-connection` 3c | populated | error |  | `CAP-PROJ-project-connections` | The request error is shown without claiming the rejected change was saved. |
| Leave the section | global: move to another project section | populated, error | populated | `UX-project-detail` |  | The selected project section replaces the form. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectSettingsForm.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectAutomation.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectDetailView.svelte`

Inspected check: `ProjectDetailView.integration.test.ts` covers the general save, the automation save with its
loaded revision and untouched verification, and a cleared run limit. The content and transitions are derived from
source inspection. This document does not assert live GitHub/provider verification.
