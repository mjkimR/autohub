---
id: PROP-sdd-milestone-readiness-target
title: Living Spec targets for PROP-sdd-milestone-readiness
summary: "Candidate contract and interface updates for preview executable sdd milestone work."
status: draft
proposal: PROP-sdd-milestone-readiness
created_at: 2026-11-05
targets:
  - file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
  - file: docs/ux/repository/UX-repository.md
  - file: docs/ux/sdd/UX-sdd-execution.md
  - file: docs/usecases/sdd/UC-preview-sdd-milestone.md
  - file: docs/ux/sdd/UX-sdd-milestone-preview.md
  - file: docs/steering/ux-objects.md
---

# [Blueprint] PROP-sdd-milestone-readiness: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend `CAP-SDD-native-delivery` with the pinned read-only preview interface, membership rules, exact dependency graph, bounded incomplete results and observational eligibility. Keep batch execution excluded. Keep `CAP-DOC-repository-viewer` read-only and describe only its navigation link to the separate Hub panel. Preserve runtime ownership in `CAP-SDD-runtime-isolation`.

## 2. Use Cases and Interface Plan

Create UC-preview-sdd-milestone for this observation goal, with these steps:

1. Choose the repository ref and milestone.
2. Request preview and inspect its captured SHA, completeness and limits.
3. Inspect member eligibility, exact prerequisite holds and related activity links.
4. Select an eligible subset and review its deterministic suggested order.
5. End inspection or refresh; later execution uses its own admission flow.

Each step cites UX-sdd-milestone-preview. Link `UC-inspect-repository-documents` to step 1 through the repository surface. Keep `UC-start-sdd-activity`'s start goal intact; add the rule that preview evidence never substitutes for its fresh admission. `UX-repository` links the panel; `UX-sdd-execution` retains existing PR-bound readiness rather than absorbing milestone selection.

### Screens

#### Candidates and recommendation

- **A — separate Hub panel (recommended)**: Keep the milestone selector, captured basis and readiness table together beside repository/native execution content. Row detail holds exact prerequisite evidence. A selection summary follows the table. This keeps the review goal in one place and does not depend on vendor selection state.
- **B — dedicated Hub preview screen**: Navigate from the repository surface to a screen with a full-width member table and a separate review step for the selection. This gives more room for large graphs, but adds navigation/state restoration for a bounded 50-member preview. Defer this alternative unless the bounded panel proves insufficient.

The recommendation is a routine design assumption within the authorized read-only scope. Optional independent UX review was requested and is recorded in this bundle's envelopes.

#### UX-sdd-milestone-preview — panel draft

**Purpose**: Review an exact milestone's currently eligible activities and an explicit local subset. The facts needed are repository/ref/SHA, milestone identity, completeness and prerequisite reasons. Runtime diagnostics and related executions are secondary disclosures.

**Content**: The member table is primary. The captured basis and completeness notice sit above it; local selection and suggested order follow it. Row details reveal exact dependency anchors and activity links. Style follows `modules/hub-ui/src/routes/layout.css` and existing repository controls.

- Repository viewer: project/repository, ref, captured SHA and refresh control.
- Repository viewer: milestone selector and Preview milestone action.
- SDD unit: member rows with exact proposal IDs/paths.
- SDD unit: eligibility, proposed Planning or handoff-first Development, exact prerequisite reasons, selection checkbox when eligible.
- Native SDD activity: timestamped workflow/runtime evidence and existing activity links, when available.
- PR run: existing project-scoped execution/PR link, when recorded.
- SDD unit: selected activities and suggested order, only for a complete preview.

**States**:

- `empty`: No milestone selected or no members found; choose a milestone or refresh. A complete zero-member result says no direct proposal members rather than completed delivery.
- `loading`: Announce preview progress, disable selection, retain the requested ref/milestone visibly and permit cancellation by changing context.
- `populated`: Show all bounded rows, exact basis and unchecked eligible choices. Inspect rows, select a subset or refresh.
- `held`: Show nonselectable held rows with dependency or admission reasons; inspect source or choose other eligible rows.
- `incomplete`: Announce exact missing coverage/limits above the table; disable selection/order and offer refresh or another milestone.
- `selected`: Show selected IDs/activity kinds and deterministic order with an observation-only notice; allow deselection, clear or end inspection.
- `stale`: On context change/refresh discard result and selection, then request the current context. Ignore a late obsolete response.
- `error`: Show access/ref/runtime/request error with applicable retry or corrected selection; no readiness is retained.

**Interactions**:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose ref/milestone | UC-preview-sdd-milestone 1 | empty, loading, populated, selected, held, incomplete, error | stale | | `CAP-SDD-native-delivery` | Prior selection clears and the chosen basis appears. |
| Preview or refresh | UC-preview-sdd-milestone 2 | empty, populated, selected, held, incomplete, error | loading | | `CAP-SDD-native-delivery` | Prior selection clears; obsolete responses are invalidated. Matching basis, completeness and member rows appear, or the exact refusal appears. |
| Expand member prerequisites | UC-preview-sdd-milestone 3 | populated, held, incomplete | same | | `CAP-SDD-native-delivery` | Exact prerequisite IDs, anchors, status and hold reasons appear. |
| Open source anchor | UC-preview-sdd-milestone 3 | populated, held, incomplete | same | `UX-repository` | `CAP-DOC-repository-viewer` | Read the anchor at the captured SHA. |
| Open existing execution | UC-preview-sdd-milestone 3 | populated, held | same | `UX-run-decisions` | `CAP-SDD-native-delivery` | Open recorded run without resuming or approving it. |
| Select/deselect eligible member | UC-preview-sdd-milestone 4 | populated, selected | selected | | `CAP-SDD-native-delivery` | Exact subset/order changes; no execution starts. |
| Clear selection | UC-preview-sdd-milestone 4 | selected | populated | | `CAP-SDD-native-delivery` | Selected count returns to zero. |
| End inspection | UC-preview-sdd-milestone 5 | populated, selected, held, incomplete, error | end | back | `CAP-SDD-native-delivery` | Return to repository content without saving a queue. |

**Register changes**: Extend the SDD unit row with milestone member/prerequisite representation and select subset, inspect order and clear selection actions. Extend Repository viewer representations with milestone selector and captured preview basis, plus Preview milestone action. Do not add Work Plan/Work Item rows or rename existing terms. These are representations of existing objects, not a new execution domain object.

## 3. Architecture and Decision Impact

Retain the boundary in `PADR-milestone-readiness-boundary` and promote its clauses into `CAP-SDD-native-delivery` upon acceptance/handoff. No new runtime owner, execution ledger, vendor fork or SDK behavior is proposed. A new service/component fits the existing feature structure; no architecture document change is required.

## 4. Development Conventions and Governance

No devkit governance or toolchain change is proposed. Regenerate the typed UI client after API schema changes. Preserve owner-specific access and runtime identity. Add reciprocal CAP/UC/UX links for retained drafts and verify the object register against implementation.

## 5. Before and After

Before: milestone documents link to proposal anchors and individual activity controls. After: a separate Hub panel reviews a bounded snapshot, exact prerequisites and a local eligible subset without creating execution artifacts. No speedup or count reduction is claimed.
