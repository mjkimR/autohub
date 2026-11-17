---
id: CAP-DOC-repository-viewer
title: Repository document and execution inspection
summary: "Render branch-specific SDD documents in Hub with safe Markdown, document navigation and validated unit/ref selections. Inspection preserves execution context without starting or approving work."
area: repository
status: active
usecases:
  - UC-inspect-repository-documents
entrypoints:
  - modules/hub/app/features/project_management/repositories/api/v1.py
  - modules/hub/app/features/project_management/repositories/services.py
  - modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte
---

# [CAP-DOC-repository-viewer] Repository document and execution inspection

## 1. Summary

The repository browser reads GitHub through the project's connector. SDD projects
use Hub-owned document navigation and rendering, with execution links and
separate activity-start controls. The selected branch determines the document view.
Activity starts forward intent without evaluating repository readiness. Retained
native decision evidence is read-only; ordinary PR questions use their Run controls.

## 2. Scope & Boundary

- **In-Scope**: repository information, directory/file reads, authenticated viewer
  transport, native Markdown/diagram rendering, document indexes, release handbook,
  branch-specific roadmap inspection and recorded execution lineage.
- **Out-of-Scope**: GitHub repository storage; activity orchestration owned by
  `CAP-SDD-native-delivery`; document authoring; repository edits.
- **Scope Excluded**: read-triggered execution or approval, cross-branch roadmap
  aggregation, inferred lineage from similar slugs, milestone batch execution and
  Work Plan linkage.

## 3. Business Rules & Policies

1. **Project connection**: WHEN a repository read is requested, Hub MUST resolve
   the repository and connector from the project or refuse missing GitHub
   configuration with HTTP 422 / `INVALID_REQUEST`.
   Source: [usecases.py](../../../modules/hub/app/features/project_management/repositories/usecases.py).
2. **Read identity**: WHEN the native viewer reads files, its data source MUST
   preserve the project, path, selected ref and cancellation signal through the
   authenticated API client and its session renewal.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `viewer requests renew the session and preserve project, path, ref and cancellation`.
3. **Incomplete branches**: IF branch enumeration fails or reaches its ten-page
   limit without a short page, THEN Hub MUST mark `branches_complete: false`
   instead of presenting its branch list as complete.
   Check: [test_repository_services.py](../../../modules/hub/tests/unit/features/project_management/repositories/test_repository_services.py), `test_branch_listing_reads_later_pages_and_reports_incomplete_results`.
4. **Viewer ref refusal**: IF branch enumeration is incomplete, THEN the repository
   data source's `refs` operation MUST report an error rather than return complete
   reference coverage.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `roadmap refs include activity branches and disclose incomplete enumeration`.
5. **File representation**: WHEN reading a file, Hub MUST return its path, ref,
   size, SHA and content with `encoding: utf-8` when decoding succeeds or
   `encoding: base64` otherwise.
   Source: [services.py](../../../modules/hub/app/features/project_management/repositories/services.py); schema/UTF-8 examples: [test_repository_services.py](../../../modules/hub/tests/unit/features/project_management/repositories/test_repository_services.py), `test_repo_blob_utf8_decode`.
6. **Selected-branch roadmap**: WHEN opening a milestone member, the native
   viewer MUST read its direct proposal anchor from the selected branch for global
   or package roadmap roots, including each root's `_archive`.
   Check: [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts), `embedded progress opens selected-branch proposal members of %s`.
7. **Recorded lineage**: WHEN retrieving related executions, Hub MUST limit results
   to the requested project and exact unit or recorded `handoff_from` lineage.
   Check: `modules/hub/app/features/project_management/sdd/repos.py` and activity history API tests.
8. **Read-only execution links**: WHEN listing a unit's related executions, Hub
   MUST return at most the latest 20 runs without advancing them.
   Check: activity history API tests; [SddRunLinks.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.integration.test.ts), `a selected proposal links its run and GitHub pull request`.
9. **Visible refusal**: IF a repository API read is refused, THEN the repository
   data source MUST propagate its error rather than supply fabricated contents.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `repository refusals propagate to the native viewer`.

10. **Descriptive progress**: WHEN an SDD repository is inspected, Hub MUST keep milestone/document navigation separate from activity execution intent. Progress groups direct milestone members, other proposals and spec anchors (newest first) with their document status and the latest PR run per activity recorded for that exact unit, read from at most the project's latest 300 runs. It links to documents, runs and decisions only, never starts work, and provides no executable readiness preview, eligible ordering or inferred proposal-to-spec lineage. IF the runs cannot be read, THEN document statuses remain with a Retry. Check: [progress.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/documents/progress.test.ts), [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts) and `ProgressList.svelte` source inspection.

11. **Addressed unit**: WHEN a Repository URL names a recognized proposal/spec directory, Hub MUST validate its document at the explicit browse ref or default branch before selecting it in both viewer and activity context. A missing explicit branch never falls back. Check: `repository-selection.integration.test.ts` and `RepositoryView.integration.test.ts`.
12. **Selection isolation**: WHEN project or unit/ref address changes, Hub MUST reject older read results and retain the current requested subject or its explicit unavailable state. Check: `RepositoryView.integration.test.ts` pending-directory navigation regression.

13. **Native presentation**: WHEN SDD documents are displayed, Hub MUST render its own controls with the shared component and theme system. Check: native viewer source, UI lint and `NativeSddViewer.integration.test.ts`.
14. **Sanitized content**: WHEN Preview renders Markdown or Mermaid, Hub MUST sanitize the resulting HTML/SVG before insertion. Check: `documents.test.ts` and `diagrams.test.ts`.
15. **Listing honesty**: IF directory or file discovery fails, THEN Hub MUST expose the incomplete listing and Retry instead of claiming an empty complete result. Check: `documents.test.ts` and native viewer state tests.
16. **Document references**: IF an inline document ID is absent, duplicated or indexed only partially, THEN Hub MUST explain the unresolved reference without opening an arbitrary document. Check: `NativeSddViewer.integration.test.ts` and document model tests.
17. **Read isolation**: WHEN the source, branch, section or selected file changes, Hub MUST prevent older asynchronous results from replacing the current document or selection callback. Check: native viewer and host integration tests.
18. **Handbook identity**: WHEN a release handbook language is selected, Hub MUST read that language's README and linked pages from the selected branch. Check: native viewer handbook integration and manifest tests.
19. **Binary presentation**: IF a selected file is base64 encoded, THEN the native viewer MUST show a binary explanation with a return action instead of parsing it as Markdown. Check: native viewer binary integration.

20. **Document addresses**: WHEN an operator selects a file in either viewer, Hub MUST synchronize its path/ref URL and restore that file across viewer modes and reload. Check: `RepositoryView.integration.test.ts` Git Browser address regression.
21. **Cleared selection**: WHEN browser history removes the document address or native section navigation clears selection, Hub MUST remove the previous preview and contextual unit actions. Check: `RepositoryView.integration.test.ts` empty-address and section-navigation regressions.
22. **Progressive discovery**: WHILE document discovery continues, Hub MUST expose completed sorted batches for inspection. Check: `documents.test.ts` progressive discovery case.
23. **Viewer read cache**: WHEN a successful tree/blob read repeats in the same viewer session and ref, Hub MUST reuse its retained result until refresh/reconfiguration or bounded eviction. Check: `read-cache.test.ts` and native viewer address/cache integration test.
24. **Read economy**: WHEN the native viewer lists directories of a ref, it MUST answer them from one whole-tree listing per ref and viewer session, and MUST fall back to directory reads when that listing fails or is truncated. WHEN a file read names a blob SHA from that listing, Hub MAY answer it from an in-process cache keyed by repository and blob SHA (immutable content, least-recently-used within 32 MiB); it caches only successful reads of files up to 1 MiB and never shares entries across repositories. A read without a SHA always goes to GitHub. WHEN Hub holds the ETag of an earlier successful read of the same GitHub URL and parameters, it MUST send it as `If-None-Match` and answer an HTTP 304 with the held body; it keeps that in-process store least-recently-used within 2,048 entries and 32 MiB, skips bodies over 8 MiB and responses without an ETag, never stores an error response and does not key by token, because GitHub authorizes each conditional request before answering 304. Check: [read-cache.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/documents/read-cache.test.ts) and [test_repository_services.py](../../../modules/hub/tests/unit/features/project_management/repositories/test_repository_services.py), `test_whole_tree_listing_maps_entries_and_reports_truncation`, `test_blob_read_with_a_known_sha_reuses_cached_content`, `test_repository_reads_revalidate_with_etags_and_reuse_bodies_on_not_modified`, `test_repository_read_errors_are_never_cached_and_keep_their_classification`, `test_conditional_cache_evicts_least_recently_used_within_its_bounds`.

## 4. Interfaces & Data Contracts

| Interface | Input / result |
| --- | --- |
| `GET /api/v1/projects/{project_id}/repository/info` | `repository`, `default_branch`, `branches_complete`, `branches` |
| `GET /api/v1/projects/{project_id}/repository/tree` | Optional `path` and `ref`; returns path/ref and items with name/path/type/size/SHA |
| `GET /api/v1/projects/{project_id}/repository/paths` | Optional `ref` (default branch when empty); one recursive GitHub tree read returning the root tree SHA, `truncated` and every file/directory item (symbolic links and submodules omitted); a GitHub-truncated or over-20,000-entry tree returns `truncated: true` with no items |
| `GET /api/v1/projects/{project_id}/repository/blob` | Required `path`, optional `ref` and 40-hex `sha` from a listing of the same ref; returns path/ref/size/SHA/encoding/content |
| `GET /api/v1/projects/{project_id}/sdd/runs` | Required `spec_dir`; returns latest 20 project-scoped related `PipelineRunRead` records |

An empty `ref` leaves branch selection to GitHub's Contents API. Directory listings
sort directories before files, then names case-insensitively. Non-file/directory
entries are omitted. Branch enumeration reads at most 1,000 entries and retains
the default branch even when enumeration is incomplete.

`project_type: general` uses the Git browser; `project_type: sdd` defaults to
`SDD View` and permits `Git Browser`. The SDD viewer starts in Documents unless a file/unit address selects its exact document. Proposal anchors open in Proposals, spec files in Specs, and other addressed files in Files. Selecting
`docs/proposals/PROP-<slug>/proposal.md` or a file under `specs/YYYY-MM/<unit>/`
shows contextual unit actions and execution history; it does not submit an execution request.
Milestone roots are `docs/roadmap/` and `docs/packages/<name>/roadmap/`, each with
flat `_archive/`. Proposal anchors establish milestone membership; historical spec
milestone fields do not.

### Repository subject addresses

`?tab=repository&path=<file>&ref=<branch>` selects an exact file.
`?tab=repository&unit=<directory>&ref=<branch>` selects a recognized `docs/proposals/PROP-<slug>` or `specs/YYYY-MM/<unit>` directory.
The optional `ref` is the visible browse branch; run-generated addresses retain the Run branch for unmerged units.
It is not immutable PR-head evidence or execution authority.
Successful selection canonicalizes to path/ref. Reload and viewer-mode changes preserve the addressed file; browser query navigation replaces or clears selection. Native section/directory navigation clears obsolete file addresses.
Invalid, missing, inaccessible or non-SDD unit requests show Unit unavailable, Retry for read failure and Browse repository.
Browse clears the unit and resets an unavailable explicit ref to default.
An unavailable unit supplies no activity-start control for that subject.
Repository subject navigation supports unit/ref selection; SDD activity claim links resolve through their current unit.

### Native document views

| View | Available content |
| --- | --- |
| Documents | Default searchable Markdown index under `docs/`, excluding proposal bundles |
| Proposals | Direct proposal anchors under `docs/proposals/PROP-<slug>/proposal.md` |
| Specs | Markdown documents under dated `specs/` bundles |
| Progress | Global/package milestones and archives with descriptive dependency statuses and direct proposal members, other proposals and spec anchors, each with document status and latest PR runs |
| Handbook | Release tag and language-specific pages from `handbook/manifest.json` |
| Files | Directory/file inspection, including other files inside proposal bundles |

Hub compiles its own viewer source into the SPA. Repository UI has no devkit-viewer package, tarball or provenance receipt. `ADR-native-sdd-viewer` records this ownership decision. Hub's repository data source, proposal activity controls and descriptive execution panel remain separate from reading. Activity base defaults to the document browse branch while remaining independently editable with a visible difference notice.

Discovery publishes completed batches before its scan finishes. Successful tree/blob reads are cached separately by ref/path, up to 300 entries per read kind in one viewer session. Failed or canceled reads are not cached. Explicit Refresh creates a fresh session while preserving the addressed file. This does not establish a live-provider latency guarantee.

Preview displays YAML metadata and sanitized Markdown; Source preserves escaped file content. Repository-relative links stay on the selected branch. Inline full document IDs are resolved on demand against all Markdown documents under `docs/` and `specs/`, including proposal bundle companion files. Missing or duplicated IDs show an error instead of choosing an arbitrary match. External HTTP/HTTPS links open with `noopener noreferrer`. Relative images are represented by their alternative text because raw repository URLs do not carry the authenticated data-source contract.

Handbook requires a string `tag` and safe `langs` including `en`; a language selects `handbook/<lang>/README.md`. Optional roots are discovered from successful parent listings. Missing roots are empty states; refused reads and malformed manifests remain errors. Mermaid uses Hub's active light/dark mode, strict rendering and sanitized SVG. Invalid diagrams retain source with an explanation. No separate viewer theme or Shared surface is exposed.

## 5. Source and Verification Boundary

Backend interfaces derive from [repositories/api/v1.py](../../../modules/hub/app/features/project_management/repositories/api/v1.py)
and [schemas.py](../../../modules/hub/app/features/project_management/repositories/schemas.py).
Native presentation and transport derive from [RepositoryView.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte)
and [data-source.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts).
Lineage and limits derive from [sdd/repos.py](../../../modules/hub/app/features/project_management/sdd/repos.py).
Native document/index, sanitizer, diagram and viewer integration tests use simulated repository reads. Binary presentation has native viewer integration coverage. These tests do not establish live GitHub reads, browser layout correctness or execution success. Actual command results and browser availability are recorded in the delivery spec envelopes.
