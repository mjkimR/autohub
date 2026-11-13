---
id: UX-repository
title: Repository Browser
summary: "The repository panel reads the selected branch through a Git browser or embedded SDD viewer and exposes descriptive activity and retained history panels for SDD projects."
area: repository
element: panel
status: active
usecases:
  - UC-inspect-repository-documents
capabilities:
  - CAP-DOC-repository-viewer
  - CAP-SDD-native-delivery
---

# [UX-repository] Repository Browser

## 1. Purpose

- **Primary task**: Inspect repository content at the selected branch.
- **Facts to commit**: Project connection repository identity, selected branch, file path and viewer mode.
- **Secondary items**: Activity intent and proposal actions occupy linked panels above the embedded viewer.

## 2. Content

The selected repository content is primary. Branch/path controls stay above it.
An SDD Project connection initially uses Sdd View and can switch to Git Browser.

- Repository viewer (branch selector and path breadcrumbs).
- Repository viewer (Git Browser directory rows, selected file and README preview).
- Repository viewer (embedded SDD document/milestone navigation in Sdd View).
- `UX-sdd-execution` (unit intent and related-run links; SDD mode only).
- `UX-sdd-proposals` (explicit activity starts; SDD mode only).

Selecting a recognized proposal/spec path carries that unit directory to the
execution panel. A browse ref is not represented as the execution PR’s head.
Optional README preview failure is silent; requested tree/file errors use the
visible retry path. Binary file handling belongs to the Git file renderer.

## 3. States

- **populated**: Browse files or SDD documents, change branch or refresh the selection.
- **empty**: Without a GitHub binding, the panel directs the operator to Connections; an empty directory retains its branch/path controls.
- **loading**: Git Browser announces initial repository loading; embedded SDD loading follows the viewer.
- **error**: Requested repository reads show an alert and Retry; failed execution lookup is distinguished within the execution panel.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose branch or file | `UC-inspect-repository-documents` 3 | populated | loading |  | `CAP-DOC-repository-viewer` | The selected ref/path content loads without mutating the repository. |
| Refresh / Retry | `UC-inspect-repository-documents` 4 | error | loading |  | `CAP-DOC-repository-viewer` | The requested read is retried; SDD refresh reloads repository identity and remounts its viewer. |
| Sdd View / Git Browser | global: choose a read-only repository representation | populated | populated |  | `CAP-DOC-repository-viewer` | The selected mode replaces the content surface. |
| Directory breadcrumb / file back | `UC-inspect-repository-documents` 3a | populated | loading |  | `CAP-DOC-repository-viewer` | The selected directory or parent listing is loaded. |

## 5. Evidence

- [RepositoryView.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte).
- [FileBlobViewer.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/FileBlobViewer.svelte).
- [data-source.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts).
- [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts); test assertions were inspected.
- [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
