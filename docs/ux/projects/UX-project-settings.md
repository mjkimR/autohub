---
id: UX-project-settings
title: Project Settings
summary: "Edit the selected project connection and automation settings from the Projects quick action while preserving revision-checked saves."
area: projects
element: modal
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-project-settings] Project Settings

## 1. Purpose

- **Primary task**: update a Project connection.
- **Facts to commit**: current name, type, enabled state, selected GitHub connector, repository, verification and automation settings.
- **Secondary items**: the project detail uses the same form in separate general, connection and automation regions. The dispatch interval is edited in the Automation tab's region; `UX-schedule-configs` links each project dispatch row there.

## 2. Content

The saved configuration form is primary. General settings precede the optional GitHub section, its verification controls and its automation controls.

- Project connection (settings form): name, type, enabled flag and GitHub connection toggle.
  - Connector (GitHub selector): names and identifiers, without plaintext credentials.
  - Project connection (verification fields): repository, workflow and comma-separated required jobs.
  - AI catalog (selector) and Project connection (automation policy): catalog, merge/fix/enrollment controls, dispatch interval and concurrency. "Adopt PRs opened by agent sessions" explains that a provider session's PR becomes a PR run at CI observation.
- Save Changes: saves the loaded project revision and refreshes its parent on success.

## 3. States

- **populated**: inspect or change the loaded values and save or dismiss.
- **loading**: `Saving...` disables submission.
- **error**: a toast reports invalid input or a conflicting/stale request; the dialog remains available for correction or reloading through its parent.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save Changes | `UC-configure-project-connection` 2, `UC-configure-project-connection` 3, `UC-configure-project-connection` 2a | populated | loading | close | `CAP-PROJ-project-connections` | A success toast closes the dialog and reloads the parent; refusal leaves input available. |
| Save rejected configuration | `UC-configure-project-connection` 3a, `UC-configure-project-connection` 3b, `UC-configure-project-connection` 3c | populated | error |  | `CAP-PROJ-project-connections` | The request error is shown without claiming the rejected change was saved. |
| Dismiss dialog | global: leave project settings | populated, error | populated | close |  | The Projects screen remains available. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectSettingsDialog.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectSettingsForm.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
