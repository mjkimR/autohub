---
id: UX-project-connections
title: Project Connections
summary: "Configure a project GitHub connection and distinguish its read-only access check from isolated AI connection tests."
area: projects
element: panel
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
  - CAP-CONN-connection-verification
---

# [UX-project-connections] Project Connections

## 1. Purpose

- **Primary task**: configure and inspect a Project connection.
- **Facts to commit**: repository, connector, verification policy, saved configuration and the type of verification being requested.
- **Secondary items**: read-only checking opens a modal; provider execution evidence belongs in the separate isolated-test panel.

## 2. Content

The GitHub connection form is primary. The access-check action follows it; AI connection testing is a separate region below.

- Project connection (connection form): enabled GitHub mapping, repository and verification settings from the shared form.
  - Connector (selector): saved GitHub connector name and short identifier; no credential contents.
- Project connection (retained automation): the connection-only form preserves saved automation and catalog values; edit those controls through `UX-project-settings` or the Automation tab of `UX-project-detail`.
- Project connection (read-only access report): `UX-connection-test-check`, available after GitHub is connected.
- Connection test (provider recipe and results): `UX-connection-tests`.

The panel is the Connections tab of `UX-project-detail`.

## 3. States

- **populated**: inspect or save repository/verification settings, open the access check or review provider tests.
- **empty**: GitHub can be disconnected; enable it and supply the required connection fields.
- **loading**: the save action reports `Saving...` and disables duplicate submission.
- **error**: save errors appear as toasts; correct input or reload the project before retrying stale edits.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select connector / supply repository and policy | `UC-configure-project-connection` 1, `UC-configure-project-connection` 2 | populated, empty | populated |  | `CAP-PROJ-project-connections` | The form shows selected connection metadata without revealing stored credentials. |
| Save Changes | `UC-configure-project-connection` 3, `UC-configure-project-connection` 2a | populated | loading |  | `CAP-PROJ-project-connections` | A success toast and parent reload expose saved configuration; prior check evidence is refreshed with the project. |
| Inspect saved configuration | `UC-configure-project-connection` 4 | populated | populated |  | `CAP-PROJ-project-connections` | Saved values are shown; the containing project list exposes its revision. |
| Save rejected configuration | `UC-configure-project-connection` 3a, `UC-configure-project-connection` 3b, `UC-configure-project-connection` 3c | populated | error |  | `CAP-PROJ-project-connections` | Validation, uniqueness or revision failure is reported by toast. |
| GitHub access check | `UC-configure-project-connection` 5 | populated | populated | `UX-connection-test-check` | `CAP-PROJ-project-connections` | The representative-PR check modal opens. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectConnections.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ProjectSettingsForm.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
