---
id: SPEC-native-sdd-viewer
title: Native SDD repository viewer
summary: "Replace the embedded devkit viewer with Hub-owned document navigation and rendering while preserving branch-specific inspection and execution context."
status: completed
created: 2026-11-16
related_capabilities: [CAP-DOC-repository-viewer]
related_usecases: [UC-inspect-repository-documents]
workflow: sdd-spec-feature
---

# [SPEC-native-sdd-viewer] Native SDD repository viewer

## 1. Problem Statement & Motivation

The embedded viewer owns its navigation, palette and theme independently of Hub. Its unsupported Shared surface and duplicated proposal navigation obscure the operator's document and activity context. Hub will own repository presentation while devkit continues to own repository workflow interpretation.

## 2. User Stories

- **US-1**: As an operator, I want branch-specific SDD documents in Hub's visual language so that I can inspect work and follow its recorded executions.
- **US-2**: As a contributor, I want the viewer source in Hub so that a document UI change does not require rebuilding devkit's viewer artifact.

## 3. Non-Goals

1. **Scope Excluded**: Changes to activity execution, workflow authority, database schemas, GitHub storage, document editing, cross-branch roadmap aggregation or repository readiness evaluation.
2. **Scope Excluded**: Replication of the standalone viewer's Dashboard and unsupported Shared backend. Document navigation replaces Dashboard summaries. Local Planning overlays remain outside Hub.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Native presentation and dependency independence
- **Given** an SDD project in either Hub theme.
- **When** Repository opens.
- **Then** Hub-owned Documents, Proposals, Specs, Roadmap, Handbook and Files controls use shared components and tokens, without a viewer theme toggle or Shared tab; no devkit-viewer dependency, artifact or receipt remains.

### [AC-02] Branch-specific document exploration
- **Given** docs, proposal bundles and dated specs on a selected branch.
- **When** the operator filters documents or opens a file.
- **Then** the selected branch is used for every read, title/ID/status/path are inspectable, partial listing failures are visible with Retry, and empty optional roots are distinguished from refused reads.

### [AC-03] Safe document rendering and navigation
- **Given** a Markdown file with YAML metadata, headings, links and Mermaid blocks.
- **When** Preview or Source is selected.
- **Then** Preview renders sanitized Markdown, metadata and diagrams using Hub theme, repository-relative links and unambiguous document IDs navigate within the selected branch, heading anchors work, and Source preserves the exact text; binary content is explained without decoding it as Markdown.

### [AC-04] Read-only milestone inspection
- **Given** global or package roadmap roots, including their flat archives, and direct proposal anchors.
- **When** a milestone or member is opened.
- **Then** only the selected branch supplies documents, dependencies are descriptive, and a direct member opens its proposal without starting work.

### [AC-05] Address and selection isolation
- **Given** an addressed unit/ref or a read pending for an older project, branch or file.
- **When** navigation, refresh, mode switch or an unavailable address occurs.
- **Then** the current document and activity context retain the validated subject, stale results cannot replace it, explicit missing refs never fall back, and no read starts or approves execution.

### [AC-06] Release handbook
- **Given** an optional handbook/manifest.json containing tag and langs including en.
- **When** Handbook opens or its language changes.
- **Then** the selected branch supplies handbook/<language>/README.md and relative pages, the release tag is displayed, absent handbooks explain their absence, and invalid or refused manifests expose an error and Retry.

### [AC-07] Toolchain and compatibility checks
- **Given** the viewer dependency is removed.
- **When** check-devkit runs.
- **Then** it validates Python devkit pin consistency without requiring any viewer files, and a regression rejects independently drifting Python pins.

## 5. Screens

### Repository document panel (revision of `UX-repository`)

**Use cases**: `UC-inspect-repository-documents`. Host coverage retains steps 1–2 and extensions 1a, 2a and 3b. Linked execution panels retain steps 5–6 and extensions 5a–5c.

**Purpose**: Inspect the selected repository branch and document. Existing branch controls remain above the content. Activity intent remains in `UX-sdd-execution` and `UX-sdd-proposals` with an explicit execution base; document browsing grants no execution authority.

**Content**:
- Repository viewer: shared native section controls; Documents is the default.
- Repository viewer: searchable title/ID/status/path document list beside the selected preview on wide screens, stacked on narrow screens.
- Repository viewer: metadata, Preview/Source, document headings and relative navigation.
- Repository viewer: read-only milestone dependency/member list in Roadmap.
- Repository viewer: release tag and language selector in Handbook.
- Repository viewer: directory/file navigation in Files; existing Git Browser remains available.

**States**:
- **populated**: Search, switch section, open a document, use Preview/Source, follow headings and related Run/PR links.
- **empty**: Explain missing section or handbook; choose another section or Git Browser.
- **filtered-empty**: Explain no matching documents and offer Clear search.
- **binary**: Show the file path and binary explanation with Back to files.
- **loading**: Static role=status identifies the requested read; controls permit switching subjects.
- **error**: Keep partial listing evidence where available, expose read failures and Retry; never report failed reads as empty success.
- **unit-unavailable**: Existing validated-address refusal, Retry and Browse repository remain in the host.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Switch section / search / open document | `UC-inspect-repository-documents` 3 | populated, empty | loading | | `CAP-DOC-repository-viewer` | Read the selected branch and name the selected path. |
| Preview / Source / heading | `UC-inspect-repository-documents` 4 | populated | populated | | `CAP-DOC-repository-viewer` | Show rendered or exact source content, or move to a heading. |
| Open milestone member / repository link | `UC-inspect-repository-documents` 3 | populated | loading | | `CAP-DOC-repository-viewer` | Open the linked document on the same branch. |
| Change handbook language | `UC-inspect-repository-documents` 4 | populated, error | loading | | `CAP-DOC-repository-viewer` | Name the language and requested README path; retain the active selection and offer Retry on failure. |
| Open ordinary / binary file | `UC-inspect-repository-documents` 3a, `UC-inspect-repository-documents` 4a | populated | populated, binary | | `CAP-DOC-repository-viewer` | Display content or a binary explanation and Back to files. |
| Retry | `UC-inspect-repository-documents` 4b | error | loading | | `CAP-DOC-repository-viewer` | Repeat the current read. |
| Git Browser | global: choose file representation | populated, empty, error | populated | | `CAP-DOC-repository-viewer` | Return to the host browser. |

## 6. Assumptions & Invariants

- Base is local main at 71fa79386efdf617396c5a85ea746a3bdde601d5; no prerequisites or active specs were found there.
- Work runs in dev-native-sdd-viewer, created directly from main because the original checkout holds another task's uncommitted changes. No implicit fetch or base checkout switch is needed.
- The runtime identity constraint in `ARCH-02-constraints` changes through ADR-native-sdd-viewer before implementation; Python pin guarantees remain.
- `docs/steering/visual-style.md` and the Repository viewer / SDD unit object rows apply. No domain object is introduced.
