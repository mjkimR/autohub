---
id: UX-repository
aliases: [UX-sdd-milestone-preview, UX-sdd-batch]
title: Repository Browser
summary: "Inspect branch-specific documents through Git Browser or native SDD view with validated unit/ref addresses and activity Run links. Unavailable subjects and stale reads preserve exact requested identity."
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
- **Secondary items**: Unit status, activity intent with its local start outcome, PR runs for the unit and collapsed PR enrollment occupy the selected unit work panel. Original request recovery stays above both viewer modes.

## 2. Content

The selected repository content is primary. Branch/path controls stay above it.
An SDD Project connection initially uses SDD View and can switch to Git Browser through a labelled two-button mode group whose selected mode uses the secondary variant.

- Repository viewer (branch selector and path breadcrumbs).
- Repository viewer (Git Browser directory rows, selected file and README preview).
- Repository viewer (native Documents, Proposals, Specs, Roadmap, Handbook and Files navigation in SDD View).
- `UX-sdd-execution` (selected-unit status, PR runs for the unit and collapsed existing-PR enrollment; SDD mode only).
- `UX-sdd-proposals` (contextual activity form for the selected proposal; SDD mode only).

Selecting a recognized proposal/spec path shows that unit directory in the contextual work panel. A browse ref is not represented as the execution PR’s head.
A recognized `unit` query validates and opens its spec/proposal document and activity selection together.
An explicit `ref` names the visible browse branch, including an unmerged Run branch; absence uses the default.
Successful file selection stores path/ref in the URL. Viewer-mode changes and reload restore the addressed file. Same-project browser history replaces or clears the selected document; explicit section/directory navigation clears an obsolete native file address.
Optional README preview failure is silent; requested tree/file errors use the
visible retry path. Both viewers explain binary content without parsing it as Markdown.

SDD content shares Hub theme and controls. A searchable title/ID/status/path list sits beside the primary document on wide screens and above it on narrow screens. Metadata, Preview/Source and heading navigation belong to the selected document. Roadmap exposes descriptive dependencies and direct proposal members. Handbook exposes the release tag, active language and home action. Activity base branch defaults to the browse branch, remains editable, and discloses an intentional difference. Unit actions sit beside the document at extra-wide widths and below it on smaller screens, where a Work on this unit button above the document moves focus to them.

## 3. States

- **populated**: Browse files or SDD documents, change branch or refresh the selection.
- **empty**: Without a GitHub binding, the panel directs the operator to Connections; an empty directory retains its branch/path controls.
- **loading**: Git Browser announces initial repository loading; native SDD loading names the section or path and selected branch. Completed discovery batches remain searchable/openable while later batches load.
- **error**: Requested repository reads show an alert in plain words with Retry; failed PR run lookup is distinguished within the unit work panel.

- **unit-unavailable**: the requested unit/ref is invalid, missing, inaccessible or unsupported. Only the alert, Browse repository and, for read failures, Retry unit appear; the SDD viewer card is not rendered. Browse repository clears the unit and resets a missing addressed ref. No start control for an unknown unit appears.
- **filtered-empty**: No matching documents offers Clear search.
- **binary**: The file path and binary explanation offer Back to files.
- **handbook-empty**: No release handbook directs the operator to Documents or Files.
- **partial-listing**: Available documents remain visible with an incomplete-list alert and Retry documents.


## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose branch or file | `UC-inspect-repository-documents` 3 | populated | loading |  | `CAP-DOC-repository-viewer` | The selected ref/path content loads without mutating the repository. |
| Refresh / Retry | `UC-inspect-repository-documents` 4 | error | loading |  | `CAP-DOC-repository-viewer` | The requested read is retried; SDD refresh preserves the selected path while reloading identity and clearing session read caches. |
| Work on this unit | global: reach the unit work panel that narrow layouts place after the document | populated | populated | | `CAP-DOC-repository-viewer` | Below the extra-wide breakpoint, the unit work panel scrolls into view and takes focus. |
| SDD View / Git Browser | global: choose a read-only repository representation | populated | populated |  | `CAP-DOC-repository-viewer` | The selected mode replaces the content surface while preserving the addressed unit and branch. |
| Directory breadcrumb / file back | `UC-inspect-repository-documents` 3a | populated | loading |  | `CAP-DOC-repository-viewer` | The selected directory or parent listing is loaded. |
| Open file/unit address / Retry unit | `UC-inspect-repository-documents` 1, `UC-inspect-repository-documents` 3b | populated, error, unit-unavailable | loading | | `CAP-DOC-repository-viewer` | Only a successful current file read can expose contextual unit actions. |
| Browse repository | `UC-inspect-repository-documents` 3b | unit-unavailable, error | populated | | `CAP-DOC-repository-viewer` | The failed unit request is cleared and an unavailable ref resets to default. |

| Search / Clear search | `UC-inspect-repository-documents` 3c | populated, filtered-empty | populated, filtered-empty | | `CAP-DOC-repository-viewer` | Filter title/ID/status/path locally; clearing restores the section. |
| Preview / Source / heading | `UC-inspect-repository-documents` 4 | populated | populated | | `CAP-DOC-repository-viewer` | Show sanitized content, escaped source or the requested heading. |
| Open document link / milestone member | `UC-inspect-repository-documents` 3, `UC-inspect-repository-documents` 4d | populated | loading | | `CAP-DOC-repository-viewer` | Read the same branch; missing or ambiguous IDs show an error. |
| Handbook language / home | `UC-inspect-repository-documents` 4c | populated, error | loading | | `CAP-DOC-repository-viewer` | Name the requested language/path, display its page or offer Retry. |
| Back to files | `UC-inspect-repository-documents` 4a | binary, populated | loading | | `CAP-DOC-repository-viewer` | Read the selected file's parent directory. |
| Retry documents / document | `UC-inspect-repository-documents` 4b | error, partial-listing | loading | | `CAP-DOC-repository-viewer` | Repeat the failed directory, file or ID resolution. |

| Select document section / clear address | global: navigate without retaining obsolete file selection | populated | populated | | `CAP-DOC-repository-viewer` | Clear the old preview, URL path and contextual unit actions; transient read callbacks do not clear the address. |

## 5. Evidence

`RepositoryView.integration.test.ts` and `repository-selection.integration.test.ts` enforce direct/reloaded addresses, visible selected document, mode changes, missing branches, stale responses and ordinary branch Refresh preservation.


- [RepositoryView.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte).
- [FileBlobViewer.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/FileBlobViewer.svelte).
- [data-source.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts).
- [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts); test assertions were inspected.
- [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts); test assertions were inspected.

Native viewer integration covers search, relative links, binary reads, retry, stale responses, handbook languages and ambiguous IDs. Diagram tests cover theme input, SVG sanitization and late-render cancellation. These simulated checks do not establish browser layout or live provider behavior; executed checks are recorded in the delivery spec envelopes.
