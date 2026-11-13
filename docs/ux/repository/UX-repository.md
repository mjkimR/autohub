---
id: UX-repository
title: Repository Browser
summary: "Inspect branch-specific documents through Git Browser or SDD view with validated unit/ref addresses and independent retained batch selection. Unavailable subjects and stale reads preserve exact requested identity."
area: repository
element: panel
status: active
usecases:
  - UC-inspect-repository-documents
  - UC-execute-sdd-batch
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
- `UX-sdd-batch` (independently addressed read-only retained batch).

Selecting a recognized proposal/spec path carries that unit directory to the
execution panel. A browse ref is not represented as the execution PR’s head.
A recognized `unit` query validates and opens its spec/proposal document and activity selection together.
An explicit `ref` names the visible browse branch, including an unmerged Run branch; absence uses the default.
A `batch` query selects retained history independently, and both subjects may coexist.
Viewer-mode changes preserve the address; same-project browser query navigation replaces the requested selection.
Optional README preview failure is silent; requested tree/file errors use the
visible retry path. Binary file handling belongs to the Git file renderer.

## 3. States

- **populated**: Browse files or SDD documents, change branch or refresh the selection.
- **empty**: Without a GitHub binding, the panel directs the operator to Connections; an empty directory retains its branch/path controls.
- **loading**: Git Browser announces initial repository loading; embedded SDD loading follows the viewer.
- **error**: Requested repository reads show an alert and Retry; failed execution lookup is distinguished within the execution panel.

- **unit-unavailable**: the requested unit/ref is invalid, missing, inaccessible or unsupported. Browse repository clears the unit and resets a missing addressed ref; read failures offer Retry unit. No start control for an unknown unit appears.
- **batch-unavailable**: confined to `UX-sdd-batch`; valid unit inspection remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose branch or file | `UC-inspect-repository-documents` 3 | populated | loading |  | `CAP-DOC-repository-viewer` | The selected ref/path content loads without mutating the repository. |
| Refresh / Retry | `UC-inspect-repository-documents` 4 | error | loading |  | `CAP-DOC-repository-viewer` | The requested read is retried; SDD refresh reloads repository identity and remounts its viewer. |
| Sdd View / Git Browser | global: choose a read-only repository representation | populated | populated |  | `CAP-DOC-repository-viewer` | The selected mode replaces the content surface while preserving the addressed unit and branch. |
| Directory breadcrumb / file back | `UC-inspect-repository-documents` 3a | populated | loading |  | `CAP-DOC-repository-viewer` | The selected directory or parent listing is loaded. |
| Open unit address / Retry unit | `UC-inspect-repository-documents` 1, `UC-inspect-repository-documents` 3b | populated, error, unit-unavailable | loading | | `CAP-DOC-repository-viewer` | Only the current recognized subject can reach viewer/activity selection. |
| Open batch address | `UC-execute-sdd-batch` 1 | populated | loading | `UX-sdd-batch` | `CAP-SDD-native-delivery` | Exact retained detail loads independently of the selected unit. |
| Browse repository | `UC-inspect-repository-documents` 3b | unit-unavailable, error | populated | | `CAP-DOC-repository-viewer` | The failed unit request is cleared and an unavailable ref resets to default. |

## 5. Evidence

`RepositoryView.integration.test.ts` and `repository-selection.integration.test.ts` enforce direct/reloaded addresses, visible selected document, mode changes, missing branches, stale responses and ordinary branch Refresh preservation.


- [RepositoryView.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte).
- [FileBlobViewer.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/FileBlobViewer.svelte).
- [data-source.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts).
- [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts); test assertions were inspected.
- [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
