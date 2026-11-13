---
id: CAP-DOC-repository-viewer
title: Repository document and execution inspection
summary: "Auto Hub serves authenticated repository files and embeds the pinned devkit viewer for branch-specific documents and milestone proposals. Reading documents exposes project-scoped execution links without starting or approving work."
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
also embed the pinned `devkit-viewer` component, with Hub-owned execution links and
separate start/decision controls. The selected branch determines the document view;
a PR's inspected revision independently determines execution readiness.

## 2. Scope & Boundary

- **In-Scope**: repository information, directory/file reads, authenticated viewer
  transport, branch-specific roadmap inspection and recorded execution lineage.
- **Out-of-Scope**: devkit-viewer's Markdown/diagram/index rendering internals;
  GitHub repository storage; native SDD execution and decisions owned by
  `CAP-SDD-native-delivery`; document authoring; repository edits.
- **Scope Excluded**: read-triggered execution or approval, cross-branch roadmap
  aggregation, inferred lineage from similar slugs, milestone batch execution and
  Work Plan linkage.

## 3. Business Rules & Policies

1. **Project connection**: WHEN a repository read is requested, Hub MUST resolve
   the repository and connector from the project or refuse missing GitHub
   configuration with HTTP 422 / `INVALID_REQUEST`.
   Source: [usecases.py](../../../modules/hub/app/features/project_management/repositories/usecases.py).
2. **Read identity**: WHEN the embedded viewer reads files, its data source MUST
   preserve the project, path, selected ref and cancellation signal through the
   authenticated API client and its session renewal.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `viewer requests renew the session and preserve project, path, ref and cancellation`.
3. **Incomplete branches**: IF branch enumeration fails or reaches its ten-page
   limit without a short page, THEN Hub MUST mark `branches_complete: false`
   instead of presenting its branch list as complete.
   Check: [test_repository_services.py](../../../modules/hub/tests/unit/features/project_management/repositories/test_repository_services.py), `test_branch_listing_reads_later_pages_and_reports_incomplete_results`.
4. **Viewer ref refusal**: IF branch enumeration is incomplete, THEN the embedded
   data source's `refs` operation MUST report an error rather than return complete
   reference coverage.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `roadmap refs include activity branches and disclose incomplete enumeration`.
5. **File representation**: WHEN reading a file, Hub MUST return its path, ref,
   size, SHA and content with `encoding: utf-8` when decoding succeeds or
   `encoding: base64` otherwise.
   Source: [services.py](../../../modules/hub/app/features/project_management/repositories/services.py); schema/UTF-8 examples: [test_repository_services.py](../../../modules/hub/tests/unit/features/project_management/repositories/test_repository_services.py), `test_repo_blob_utf8_decode`.
6. **Selected-branch roadmap**: WHEN opening a milestone member, the embedded
   viewer MUST read its direct proposal anchor from the selected branch for global
   or package roadmap roots, including each root's `_archive`.
   Check: [Roadmap.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts), `embedded roadmap opens selected-branch proposal members of %s`.
7. **Recorded lineage**: WHEN retrieving related executions, Hub MUST limit results
   to the requested project and exact unit or recorded `handoff_from` lineage.
   Check: `modules/hub/app/features/project_management/sdd/repos.py` and activity history API tests.
8. **Read-only execution links**: WHEN listing a unit's related executions, Hub
   MUST return at most the latest 20 runs without advancing them.
   Check: activity history API tests; [SddRunLinks.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.integration.test.ts), `a selected proposal links its run and GitHub pull request`.
9. **Visible refusal**: IF a repository API read is refused, THEN the embedded
   data source MUST propagate its error rather than supply fabricated contents.
   Check: [data-source.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.test.ts), `repository refusals propagate to the embedded viewer`.

10. **Read-only milestone documents**: WHEN an SDD repository is inspected, Hub MUST keep milestone/document navigation separate from activity execution intent. It provides no executable readiness preview or eligible ordering. Check: repository UI integration tests and `RepositoryView.svelte` source inspection.

## 4. Interfaces & Data Contracts

| Interface | Input / result |
| --- | --- |
| `GET /api/v1/projects/{project_id}/repository/info` | `repository`, `default_branch`, `branches_complete`, `branches` |
| `GET /api/v1/projects/{project_id}/repository/tree` | Optional `path` and `ref`; returns path/ref and items with name/path/type/size/SHA |
| `GET /api/v1/projects/{project_id}/repository/blob` | Required `path`, optional `ref`; returns path/ref/size/SHA/encoding/content |
| `GET /api/v1/projects/{project_id}/sdd/runs` | Required `spec_dir`; returns latest 20 project-scoped related `PipelineRunRead` records |

An empty `ref` leaves branch selection to GitHub's Contents API. Directory listings
sort directories before files, then names case-insensitively. Non-file/directory
entries are omitted. Branch enumeration reads at most 1,000 entries and retains
the default branch even when enumeration is incomplete.

`project_type: general` uses the Git browser; `project_type: sdd` defaults to
`Sdd View` and permits `Git Browser`. The SDD viewer starts at `docs/`. Selecting
`docs/proposals/PROP-<slug>/proposal.md` or a file under `specs/YYYY-MM/<unit>/`
fills the bound unit selector; it does not submit an execution request.
Milestone roots are `docs/roadmap/` and `docs/packages/<name>/roadmap/`, each with
flat `_archive/`. Proposal anchors establish milestone membership; historical spec
milestone fields do not.

### Embedded document views

| View | Available content |
| --- | --- |
| Dashboard | Default embedded view with repository document/work summaries |
| Read | Release handbook from `handbook/manifest.json`; the Living Spec book indexes `docs/` when explicitly requested |
| Proposals | Proposal bundles under `docs/proposals/` with document filtering |
| Specs | Change-spec bundles under `specs/` with document filtering |
| Roadmap | Selected-branch milestones, dependency-readiness display and direct proposal members, including archived milestones |
| Files | Selected-branch directory/file inspection and document rendering |
| Shared | The library exposes a Shared shell, but Hub's data source supplies no shared-artifact backend capability |

Hub compiles the pinned `devkit-viewer` tarball into its SPA. It does not download a
viewer bundle or install a plugin while serving a repository view. The library
owns document parsing/rendering; Hub owns its repository data source, Proposals
controls and descriptive activity panel. These controls remain separate from reading.
The [artifact receipt and rebuild procedure](../../../modules/hub-ui/vendor/devkit-viewer.md)
identify the library source and contributor update path.

## 5. Source and Verification Boundary

Backend interfaces derive from [repositories/api/v1.py](../../../modules/hub/app/features/project_management/repositories/api/v1.py)
and [schemas.py](../../../modules/hub/app/features/project_management/repositories/schemas.py).
Embedding and transport derive from [RepositoryView.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte)
and [data-source.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/data-source.ts).
Lineage and limits derive from [sdd/repos.py](../../../modules/hub/app/features/project_management/sdd/repos.py).
The linked tests identify inspected regression evidence; schema-only or simulated
UTF-8 tests do not establish binary-file integration coverage. No live repository,
rendering or execution success is implied by source inspection alone.
