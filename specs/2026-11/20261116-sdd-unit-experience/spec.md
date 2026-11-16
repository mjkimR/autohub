---
id: SPEC-sdd-unit-experience
title: Polish the SDD unit workspace
summary: Unify repository documents, activity intent and execution history around the selected SDD unit.
status: planned
created: 2026-11-16
related_capabilities: [CAP-SDD-native-delivery, CAP-DOC-repository-viewer]
related_usecases: [UC-start-sdd-activity, UC-complete-sdd-workflow, UC-inspect-repository-documents]
workflow: sdd-spec-feature
---

# [SPEC-sdd-unit-experience] Polish the SDD unit workspace

## 1. Problem Statement & Motivation

Separate proposal actions, PR enrollment and document browsing obscure the selected SDD unit. Operators must retain the unit and branch mentally while moving between duplicate lists. Branch edits can leave stale proposal actions enabled. Full document discovery delays useful results and repeated reads discard context.

## 2. User Stories

- **US-1**: As an operator, I can read a unit and start its explicit activity beside its document (`UC-start-sdd-activity`).
- **US-2**: As an operator, I can inspect unit runs and deliberately enroll an existing PR (`UC-complete-sdd-workflow`).
- **US-3**: As an operator, I can return to an addressed document and see useful discovery results before scanning finishes (`UC-inspect-repository-documents`).

## 3. Non-Goals

1. **Scope Excluded**: Repository readiness gates, inferred workflow eligibility, new execution APIs, repository authoring and milestone execution.
2. **Scope Excluded**: A persistent backend document index or a live GitHub performance claim. Optimize successful reads and incremental presentation within the viewer session.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Contextual activity intent
- **Given** a selected proposal document on a browse branch.
- **When** the operator reviews and submits Planning or Development.
- **Then** the form identifies that proposal, activity and base; only that slug and reviewed base are sent. No duplicate proposal execution list appears above the viewer.

### [AC-02] Deliberate enrollment
- **Given** a selected proposal or spec.
- **When** the operator opens existing PR enrollment.
- **Then** its unit is identified, its PR number starts empty, and submission stays disabled until a positive integer is supplied. Related runs appear for the selected unit.

### [AC-03] Retained recovery
- **Given** an unresolved original activity or enrollment request.
- **When** the operator selects another document or switches viewer mode.
- **Then** the original request remains visible at workspace level and competing submissions stay disabled. Exact-request and claim recovery retain their existing payloads.

### [AC-04] Addressable navigation
- **Given** a selected file and branch.
- **When** the operator navigates documents, reloads or uses browser history.
- **Then** the URL identifies the selected path and ref, and the same file reopens without execution. Existing unit/ref links remain supported.

### [AC-05] Progressive and reusable reads
- **Given** document discovery containing multiple batches.
- **When** one batch completes or a previously read file is reopened.
- **Then** discovered results are usable while loading, and successful file/tree reads are reused within the same viewer branch session. Explicit refresh invalidates those reads.

### [AC-06] Presentation and isolation
- **Given** empty, populated, failed or changing repository reads.
- **When** the workspace renders or the branch changes.
- **Then** it offers contextual next actions, separates document status from run state, uses shared theme/components and ignores outdated reads. Activity base defaults to the selected browse branch while remaining explicitly editable.

## 5. Screens

### Repository workspace (`UX-repository`)

- **Purpose**: Find and inspect an SDD unit. Primary: document list and preview. Secondary: unit actions beside the selected document; global request recovery above the viewer.
- **Content**: Repository viewer branch/mode/refresh; document section and search; selected document; SDD unit directory; Native SDD activity intent; PR run history; collapsed existing-PR enrollment.
- **States**: empty offers section/file navigation; loading exposes completed discovery rows; error offers exact read retry; populated identifies branch and unit; uncertain retains the original request independently of selection.
- **Interactions**: Select file (`UC-inspect-repository-documents` 3–4) updates URL and preview; select section is global navigation; Open run (`UC-complete-sdd-workflow` 1) exits to `UX-run-page`.

### Contextual unit work (`UX-sdd-proposals`, `UX-sdd-execution`)

- **Purpose**: Request explicit work for the unit being read. Show proposal ID/path, chosen activity, base and optional effort before submission.
- **Content**: Proposal actions only for a recognized proposal; execution history for either unit kind; existing-PR enrollment in a secondary disclosure. A spec offers enrollment/history without inventing a proposal activity API.
- **States**: populated allows explicit submission; busy/uncertain disables competing starts; unselected offers document selection; error retains the current form and original request feedback.
- **Interactions**: Start activity (`UC-start-sdd-activity` 1–4) shows workspace outcome; enroll existing PR (`UC-complete-sdd-workflow` 1) shows the same outcome; Open run exits to `UX-run-page`.

## 6. Assumptions

- User accepted the preceding Unit-centered review. Keep a split list/detail workspace rather than a separate dashboard or a wizard.
- The local base is main at bb0dcfc91e1b27dca81086778f128b07888c0b65. There are no prerequisite edges or overlapping active specs.
- Optional UX review was offered. Independent code review remains required at medium effort.

## 7. UX Review Refinements

Both workspace and contextual panels serve `UC-start-sdd-activity`, `UC-complete-sdd-workflow` and `UC-inspect-repository-documents` through the following mappings.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Select document or follow relative link | `UC-inspect-repository-documents` 3, 4 | populated | loading, populated, error | `UX-repository` | URL retains path/ref; failed reads retain exact Retry document. |
| Switch branch or browse address | `UC-inspect-repository-documents` 1, 2 | populated | loading | `UX-repository` | Replace selected branch content and discard older reads; reset contextual intent to the new unit/branch. |
| Refresh | global: refresh repository evidence | populated, error | loading | | Preserve selected path and clear successful-read caches. |
| Switch viewer mode / reload / browser history | global: restore document navigation | populated | populated | `UX-repository` | Restore addressed path/ref without execution; original request stays above both modes. |
| Load or retry unit history | `UC-inspect-repository-documents` 5, 5a, 5c | loading, empty, error | populated | `UX-sdd-execution` | Show loading, no executions, or Retry history independently of the document. |
| Open run or PR | `UC-inspect-repository-documents` 6, `UC-start-sdd-activity` 5, `UC-complete-sdd-workflow` 1 | populated | populated | `UX-run-page` | Open exact retained Run or external PR. |
| Choose activity/base/effort | `UC-start-sdd-activity` 1 | populated | populated | | Show unit and base at submission; an edited base has a visible difference notice; changing unit or browse branch resets the form. |
| Start activity / enroll PR | `UC-start-sdd-activity` 2, 3, 4, `UC-complete-sdd-workflow` 1 | populated | loading | | Workspace request feedback identifies original unit/activity/base or PR, effort and request identity. |
| Retry same request | `UC-start-sdd-activity` 3b, 4a | uncertain | loading | | Send the retained identical payload; competing work remains disabled. |
| Inspect conflicting owner | `UC-start-sdd-activity` 2b | ownership-conflict | populated | `UX-sdd-claim-recovery` | Inspect retained owner/evidence; active ownership offers Run inspection; uncertain no-Run reservation retains explicit acknowledgment before release. |

History loading does not clear the selected document. An empty history explains that no recorded executions exist; failed lookup offers Retry history. Exact-request retry checks the original request through the existing idempotent endpoint. The original request region never follows the currently selected unit implicitly.
