---
id: SPEC-run-origin-links
title: Run origin links and subject deep links
summary: "Project retained run relationships in bounded reads and open exact Repository unit, branch and batch subjects without execution effects."
status: planned
created: 2026-11-13
related_capabilities: [CAP-PR-pull-request-delivery, CAP-DOC-repository-viewer, CAP-SDD-native-delivery]
related_usecases: [UC-deliver-pull-request, UC-inspect-repository-documents, UC-execute-sdd-batch]
workflow: sdd-spec-feature
---

# [SPEC-run-origin-links] Run origin links and subject deep links

## 1. Problem Statement & Motivation

Run inspection has no retained-owner projection and exact Repository links do not select their named unit. The ended-run recovery component scans Work Plans. Attention batch links omit their batch identity. Retained batch detail reads already exist and remain read-only under `ADR-repository-owned-sdd-execution`.

## 2. User Stories

- As an operator, I open a run's retained Work Item, Provider session or SDD subject without deriving owners in the browser.
- As an operator, I open a recorded unit on its run branch or an old retained batch and see the exact subject or an unavailable explanation.

## 3. Non-Goals

1. **Scope Excluded**: enrollment, execution, owner association, retention or recovery authority changes.
2. **Scope Excluded**: persisted original entry-channel provenance, schema migration or backfill.
3. **Scope Excluded**: local Provider session dialog addressing, missing-URL substitute links, native batch controls and unrelated Repository redesign.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Retained relationship projection
- **Given** runs linked to Work Items, Provider sessions or SDD claims
- **When** list, detail, SDD-unit reads or mutations return PipelineRunRead
- **Then** all distinct project-scoped relationships are sorted deterministically, Work Items include Plan IDs, sessions include catalog/session IDs and exact URL when retained, and claims include unit and optional batch ID without duplicating runs.

### [AC-02] Evidence and failure semantics
- **Given** zero, one or several retained evidence categories
- **When** a run is projected
- **Then** enrollment_source is unknown, the one proven work_plan/provider_session/native_sdd category, or multiple; nonempty SDD snapshot proves native_sdd, no manual/webhook/SDK channel is inferred, and projection failures fail the read.

### [AC-03] Bounded projection
- **Given** one-row and multi-row run pages
- **When** origins are loaded after page selection
- **Then** at most three additional bulk SELECTs run sequentially on the caller's one checked-out connection, preserving count, ordering and page membership on SQLite and PostgreSQL.

### [AC-04] Exact owner links
- **Given** an ended Work Item run or retained origins
- **When** its run page or list row renders
- **Then** compact secondary links open the exact named owners and recovery uses returned IDs without a Work Plan list request; missing external URL is text and unknown origin is explicit.

### [AC-05] Addressed unit and branch
- **Given** a valid proposal/spec directory with optional recorded ref
- **When** Repository opens, reloads, changes query or switches viewer modes
- **Then** document and activity selection agree on the validated unit at that ref, mode switches preserve selection, and a missing branch never silently falls back.

### [AC-06] Addressed retained batch
- **Given** a batch older than the latest fifty
- **When** Attention or a run opens its batch address
- **Then** exact project-scoped detail is visible without a list prerequisite, later list loading occurs once and preserves that selection, and explicit Refresh status reloads only selected detail.

### [AC-07] Unavailable subjects and stale responses
- **Given** malformed, missing, inaccessible or non-SDD subjects or an earlier pending request
- **When** lookup settles or address/project changes
- **Then** the requested subject has an unavailable explanation with Browse repository and transient Retry, no different subject replaces it, and stale responses cannot overwrite current selection.

### [AC-08] Independent selections without authority
- **Given** simultaneous unit and batch addresses
- **When** the SDD view opens
- **Then** both named regions select independently and no start/create/control mutation is sent; unavailable units enable no start controls for that unit.

### [AC-09] Retained history switching
- **Given** retained batches A and B
- **When** the operator addresses B after inspecting A
- **Then** only B's exact history is selected without resending A's control receipt or inferring execution authority.

## Screens

The accepted screen deltas in `PROP-run-origin-links-target` define secondary Related origins on the run page/list and addressed-unit/batch loading, unavailable, Retry and Browse repository states. Existing primary actions stay unchanged. Planning already offered and completed optional UX review; no screen direction is reopened in Development.

## Source feedback

- `FB-attention-sdd-batch-deep-link`: received in full; Attention must carry context.sdd_batch_id into exact historical batch inspection.

## Assumptions

- Existing project-scoped batch GET is sufficient; this feature changes its client selection, not its admission or control authority.
- Codex projection is emulated: absolute worktree paths, committed-range/snapshot audits and separate sandbox escalations substitute for native boundary enforcement.
