---
id: SPEC-owed-counts-error-reason
title: Preserve shared owed-counts failure reasons
summary: "Restore shared-store Projects failure tooltips while preserving neutral count presentation, request cadence and session fences."
status: in-progress
created: 2026-11-13
decomposed_from: PROP-hub-ui-shell-polish
related_capabilities: [CAP-PR-owed-items]
related_usecases: []
workflow: sdd-spec-bugfix
---

# [SPEC-owed-counts-error-reason] Preserve shared owed-counts failure reasons

## 1. Problem Statement & Motivation

`UX-projects` promises the failure reason in an unavailable Needs-you tooltip. The shell's shared counts store discards that reason, and Projects supplies an empty reason for its shared-context branch. Restore the existing contract without another request.

## 2. Defect Characterization

- **Current behavior**: `OwedCountsStore.refresh` ignores API errors; Projects sets its shared error to an empty string. API refusal becomes a neutral dash without the promised reason.
- **Expected behavior and its basis**: `UX-projects` Content requires the unavailable count's tooltip to name its failure reason. Existing fallback behavior already exposes API detail.
- **Behavior to preserve**: the count union, initial unknown state, known count links, shared request cadence, session-generation fence and neutral shell/Attention unknown display.
- **Reproduction conditions**: provide a real `OwedCountsStore` through `OWED_COUNTS_CONTEXT`, return API detail `Database busy`, refresh once and assert both responsive tooltip copies name that reason with one shared counts request. Record Red before the production fix.

## 3. Non-Goals

1. **Scope Excluded**: backend, API schema, polling/throttling changes, stronger per-kind validation and additional count requests.
2. **Scope Excluded**: sidebar redesign, new error presentation in shell/Attention, count layout or new primary actions.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Shared API failure tooltip
- **Given** Projects renders with the real shared counts store
- **When** one refresh returns API error detail Database busy
- **Then** both unavailable count copies show `Needs-you count unavailable: Database busy`, retain a neutral dash and add no duplicate counts read.

### [AC-02] Failure metadata and recovery
- **Given** an initially unknown store or a settled failure
- **When** an API error, thrown request, invalid total or successful response settles
- **Then** API errors use `apiErrorMessage`, thrown or invalid responses use `Needs-you counts are unavailable`, initial error is empty, success clears the error, and a pending retry preserves settled state.

### [AC-03] Session generation fence
- **Given** a request is pending when the session generation changes
- **When** its obsolete success or failure arrives
- **Then** neither the current count value nor current failure reason changes.

### [AC-04] Neutral neighboring presentation and cadence
- **Given** the shell and shared Projects context
- **When** mounting Projects or settling failed/invalid counts
- **Then** mounting adds no counts read, Refresh uses the shared request, and the shell/Attention keep their neutral unknown semantics and existing cadence.

## 5. Screens

`UX-projects` keeps its layout, controls, responsive copies and interactions. In counts unknown state, failed shared reads use the same tooltip as failed fallback reads; initial loading has no failure detail. Refresh retries through the shared store. No alternative arrangement or additional UX review is needed for this existing tooltip restoration; Planning fixed this direction at low effort.

## 6. Preserved Planning Evidence

Source inspection is retained at `docs/materials/2026-11/20261113-owed-counts-error-reason/counts-evidence.md`. It is inspection evidence, not executed regression or deployment evidence. The reproduction baseline is this worktree's product code before the fix, so no checkout is needed.
