---
id: PLAN-native-sdd-viewer
spec: SPEC-native-sdd-viewer
---

# Technical Plan: `SPEC-native-sdd-viewer`

## 1. Constitution & Invariant Review

`ADR-native-sdd-viewer` changes the viewer provenance portion of `ARCH-02-constraints` and partially supersedes the viewer update consequence in `ADR-sdd-development`. Backend layering, authentication and repository workflow authority remain unchanged. No API or persisted schema changes are needed.

## 2. Architecture Overview & Impact

Hub owns a native repository document panel. Existing authenticated repositoryDataSource is its transport and owns concrete Hub types rather than extending the vendor contract. The native panel replaces the component import and uses existing host branch/unit validation. Existing execution and proposal panels remain explicit mutations outside document rendering.

Markdown, DOMPurify, YAML and dynamically loaded Mermaid remain direct dependencies. The devkit-viewer tarball, receipt, dependency and integrity checks are removed. No vendor component source is copied.

## 3. Component & Interface Design

- repository documents: typed metadata parsing, path resolution, bounded concurrent directory discovery, section-specific indexes and descriptive milestone membership.
- document rendering: sanitized HTML, heading slugs, safe relative links, unique ID references and themed Mermaid diagrams; Source is escaped raw text.
- native viewer: native shared section controls, search/list, selected document, Files browser, Roadmap and Handbook. Each read owns an AbortController and a generation fence.
- RepositoryView: passes data source, selected branch/path and selection callback; keeps unavailable-unit guards and independently addressed batch history.

The normative transport is RepositoryDataSource.info/refs/tree/blob with AbortSignal, using RepoInfo/RepoTree/RepoBlob generated aliases. No UI operation grants workflow authority.

## 4. Storage & State Management

All document state is ephemeral and scoped to the source instance and selected ref. Section indexes are loaded on demand and reused only for that source/ref; Refresh remounts the native panel. Search is local. No new browser theme storage is introduced. Handbook language is component state.

## 5. Error Handling & Edge Cases

Discover optional roots from successful parent listings. A failed tree/blob read remains a visible error; partial listings are labeled incomplete. Validate immediate-child paths before traversing. Duplicate IDs never resolve arbitrarily. Binary blobs are not parsed as Markdown. Abort and generation checks prevent stale publication. Malformed metadata and manifests expose path-specific errors with Retry.

## 6. Verification & Test Plan

AC-01/07: dependency removal, Python checker regressions, just check-devkit and repository grep. AC-02/04: document index tests and native roadmap integration for all four root/archive cases. AC-03: Markdown/link/frontmatter tests, sanitizer and binary integration. AC-05: existing repository selection/host integration plus native stale-read tests. AC-06: manifest/language/link/error tests. Run targeted UI tests, all UI tests, pin checker unit tests, just lint and just check. UI walkthrough uses a local fixture if browser tooling is available; source/test evidence is reported separately.
