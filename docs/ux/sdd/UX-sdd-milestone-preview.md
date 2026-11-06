---
id: UX-sdd-milestone-preview
title: Preview milestone work
summary: "The repository panel inspects pinned milestone readiness and an ephemeral eligible subset, with explicit incomplete and stale states."
area: sdd
element: panel
status: active
usecases:
  - UC-preview-sdd-milestone
capabilities:
  - CAP-SDD-native-delivery
  - CAP-DOC-repository-viewer
---

# [UX-sdd-milestone-preview] Preview milestone work


## 1. Purpose

Review an exact milestone's currently eligible activities and an explicit local subset. The facts needed are repository/ref/SHA, milestone identity, completeness and prerequisite reasons. Runtime diagnostics and related executions are secondary disclosures.

## 2. Content

The member table is primary. The captured basis and completeness notice sit above it; local selection and suggested order follow it. Row details reveal exact dependency anchors and activity links. Style follows `modules/hub-ui/src/routes/layout.css` and existing repository controls.

- Repository viewer: project/repository, ref, captured SHA and refresh control.
- Repository viewer: milestone selector and Preview milestone action.
- SDD unit: member rows with exact proposal IDs/paths.
- SDD unit: eligibility, proposed Planning or handoff-first Development, exact prerequisite reasons, selection checkbox when eligible.
- Native SDD activity: timestamped workflow/runtime evidence and owned PR links, including before enrollment.
- PR run: existing project-scoped execution/PR link, when recorded.
- SDD unit: selected activities and suggested order, only for a complete preview.

## 3. States

- `empty`: No milestone selected or no members found; choose a milestone or refresh. A complete zero-member result says no direct proposal members rather than completed delivery.
- `loading`: Announce preview progress, disable selection, retain the requested ref/milestone visibly and permit cancellation by changing context.
- `populated`: Show all bounded rows, exact basis and unchecked eligible choices. Inspect rows, select a subset or refresh.
- `held`: Show nonselectable held rows with dependency or admission reasons; inspect source or choose other eligible rows.
- `incomplete`: Announce exact missing coverage/limits above the table; disable selection/order and offer refresh or another milestone.
- `selected`: Show selected IDs/activity kinds and deterministic order with an observation-only notice; allow deselection, clear or end inspection.
- `stale`: On context change/refresh discard result and selection, then choose the current milestone and request preview again. Ignore a late obsolete response.
- `error`: Show access/ref/runtime/request error with applicable retry or corrected selection; no readiness is retained.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose ref/milestone | `UC-preview-sdd-milestone` 1 | empty, loading, populated, selected, held, incomplete, error | stale | | `CAP-SDD-native-delivery` | Prior selection clears and the chosen basis appears. |
| Preview or refresh | `UC-preview-sdd-milestone` 2 | empty, populated, selected, held, incomplete, error | loading | | `CAP-SDD-native-delivery` | Prior selection clears; obsolete responses are invalidated. Matching basis, completeness and member rows appear, or the exact refusal appears. |
| Expand member prerequisites | `UC-preview-sdd-milestone` 3 | populated, held, incomplete | same | | `CAP-SDD-native-delivery` | Exact prerequisite IDs, anchors, status and hold reasons appear. |
| Open source anchor | `UC-preview-sdd-milestone` 3 | populated, held, incomplete | same | | `CAP-DOC-repository-viewer` | Open GitHub source at the captured SHA while retaining the panel. |
| Open owned PR | `UC-preview-sdd-milestone` 3 | populated, held, incomplete | same | | `CAP-SDD-native-delivery` | Open the owned PR on GitHub while retaining the panel, including before enrollment; no enrollment or resumption occurs. |
| Open existing execution | `UC-preview-sdd-milestone` 3 | populated, held | same | `UX-run-decisions` | `CAP-SDD-native-delivery` | Open recorded run without resuming or approving it. |
| Select/deselect eligible member | `UC-preview-sdd-milestone` 4 | populated, selected | selected | | `CAP-SDD-native-delivery` | Exact subset/order changes; no execution starts. |
| Clear selection | `UC-preview-sdd-milestone` 4 | selected | populated | | `CAP-SDD-native-delivery` | Selected count returns to zero. |
| Leave repository inspection | `UC-preview-sdd-milestone` 5 | populated, selected, held, incomplete, error | end | end | `CAP-SDD-native-delivery` | Navigate away without saving a queue. |

## 5. Evidence

The implemented panel and UI regression suite are `modules/hub-ui/src/lib/features/project-management/repositories/SddMilestonePreview.svelte` and `SddMilestonePreview.integration.test.ts` beside it. Style uses `modules/hub-ui/src/routes/layout.css`. Catalog and member duplicate observations retain incomplete warnings and disabled controls. Existing owned PR links remain available before enrollment; no run is invented. Execution evidence is timestamped separately from repository content. This contract follows source/test inspection; executed checks are recorded in the spec verification record, not a live browser/deployment claim.

## 6. Adjacent execution selection

`UX-sdd-batch` is a separate panel below the observational preview and is available for retained-batch lookup even without a current preview. Open execution selection uses the complete captured basis with an initially empty explicit selection. It can include supported prerequisite-held future intent. The preview's own eligible-only local subset stays observational and is never silently copied into execution selection.
