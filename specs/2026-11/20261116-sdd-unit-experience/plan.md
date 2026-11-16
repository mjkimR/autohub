---
id: PLAN-sdd-unit-experience
spec: SPEC-sdd-unit-experience
---

# Technical Plan: `SPEC-sdd-unit-experience`

## 1. Constitution & Invariant Review

No invariant changes. Preserve `ADR-native-sdd-viewer`, `CAP-DOC-repository-viewer` read isolation and `CAP-SDD-native-delivery` explicit optimistic starts and exact-request recovery. Keep APIs and repository ownership unchanged.

## 2. Architecture Overview & Impact

RepositoryView owns URL branch/path and global request outcome. NativeSddViewer owns navigation, discovery and preview, rendering a contextual unit-actions snippet. Contextual proposal activity replaces the duplicate execution list. Existing PR enrollment is a secondary disclosure for the selected unit. No dependencies or storage migrations.

## 3. Component & Interface Design

- AC-01/AC-06: SddProposals accepts selected proposal directory and browse branch, displays activity/base/effort review and submits one explicit intent. Remount on unit/ref changes.
- AC-02: SddUnitActions coordinates proposal intent, SddRunLinks history and SddExecution enrollment. The enrollment number is initially undefined and requires a positive integer.
- AC-03: SddStartOutcome moves to workspace scope with the shared SddStarts store unchanged.
- AC-04: RepositoryView writes document path/ref navigation; viewer accepts address updates separately from source configuration to prevent selection feedback loops.
- AC-05: A successful-read cache wraps the viewer data source; discovery publishes sorted partial batches guarded by generation. Refresh invalidates caches while retaining selection.

## 4. Storage & State Management

State stays in memory. Only document path and branch are URL state. Successful tree/blob reads are bounded to a viewer branch session; failures and canceled reads are not cached. Refresh clears caches. Uncertain execution remains in the existing shared per-project state.

## 5. Error Handling & Edge Cases

Keep unavailable unit/ref validation and no silent branch fallback. Changed context destroys editable forms; retained request feedback remains independent. Reading and navigation never submit work. Partial discovery displays errors alongside successful rows.

## 6. Verification & Test Plan

Run repository/viewer/activity integration and model tests for AC-01 through AC-06; add regressions for empty enrollment, selected-unit submission, retained recovery, URL restoration and progressive cached reads. Run just init hub, just lint and just check. Inspect rendered fixture UI at desktop/mobile widths when available. Record any browser coverage limit. No live GitHub execution is required.
