---
id: PROP-owed-counts-error-reason
title: Preserve shared owed-counts failure reasons
summary: "Restore the Projects Needs-you failure tooltip through the shared counts store while preserving neutral count presentation and the existing request cadence."
status: accepted
created_at: 2026-11-13
target_area: ux/projects/
priority: low
size: S
planning_effort: low
dev_effort: medium
boundaries:
  owns:
    - ux/projects/
    - modules/hub-ui/src/lib/features/attention/owed-counts.svelte.ts
    - modules/hub-ui/src/lib/features/attention/owed-counts.test.ts
    - modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.svelte
    - modules/hub-ui/src/lib/features/project-management/projects/ProjectsView.integration.test.ts
    - modules/hub-ui/src/lib/components/shared/AppShell.integration.test.ts
  excludes:
    - docs/decisions/
    - modules/hub/
    - modules/hub-ui/src/lib/api/
    - modules/hub-ui/src/routes/layout.css
task_kind: bugfix
decomposed_from: PROP-hub-ui-shell-polish
workflow: sdd-proposal
---

# [PROP-owed-counts-error-reason] Preserve shared owed-counts failure reasons

## 1. Background & Hypothesis

`UX-projects` promises a reason in the tooltip when a Needs-you count read fails. The shared shell store discards
the reason, and `ProjectsView.svelte` supplies an empty reason whenever that store exists. The fallback read already
names API failures, so the normal in-shell path violates the existing contract.

This bugfix is split from ~~`PROP-hub-ui-shell-polish`~~ at `d9cf2ae7ed792ecb8582c07d9f09979f544e26db`.
Inherited source and test inspection is retained in `materials/counts-evidence.md`. No reproduction test has run.

## 2. Planning Decisions

Source and test inspection was refreshed at `7e780ab7e45757bdf44e6edd330767f62ffd41dc`.
The evidence in `materials/counts-evidence.md` confirms the shared-path defect and the existing API message
convention. This Planning turn ran document checks, not a reproduction test or live service check.

| Question | Settled direction | Consequence |
| --- | --- | --- |
| Q1: error state | Add an initially empty reactive `error` string to `OwedCountsStore`, separate from `value`. | Existing `OwedCounts` consumers and pure count summarization retain their current shapes. Projects uses `shared.error` for its existing unavailable-count tooltip. |
| Q1: reason source | For an API error result, use the existing `apiErrorMessage` helper with `Needs-you counts are unavailable` as its fallback. Use that same fixed fallback for a thrown request or a response whose summarized total is unknown. | Structured API detail follows the existing fallback-path convention. Unexpected thrown values and invalid counts do not become diagnostic dumps or positive counts. |
| Q2: lifecycle | Commit the settled count value and error only if the captured session generation still matches. A valid count response clears the error. | An older session's completion changes neither field. Initial loading has an empty reason; a failed state keeps its reason until the next accepted response settles. |
| Q2: request reuse | Leave the in-flight guard, start/navigation/visibility cadence and shared context unchanged. | Mounting Projects makes no extra counts read. Refresh uses the same shared store. |

API refusal takes precedence over any accompanying data. A successful response whose total passes the existing
summarizer remains known; filtering invalid per-kind/per-project entries keeps its existing behavior. No stronger
counts schema validation is introduced. While an accepted refresh is pending, keep the previous settled state, as
the store already does; this repair adds no separate loading transition or retries.

The direction restores an existing tooltip contract and requires no PADR or user product choice. Planning effort
remains `low`. Development remains `medium` for shared reactive state, recovery and independent code review.

## 3. Proposed Design & Impact

1. Add the separate error metadata in `OwedCountsStore` and apply it with `value` inside the existing session fence.
2. Replace the shared branch's empty `needsYouError` in `ProjectsView.svelte` with that field. Reuse the existing
   neutral dash, title prefix and responsive copies; change no layout, focus behavior or primary action.
3. Preserve shell/Attention's neutral unknown display. Their existing count readers need no production changes.
4. Update `UX-projects` counts-unknown state wording to cover the shared and fallback failure reason, and update its
   enforcing-test evidence after Development. The existing Content contract already promises the tooltip.

`UX-projects` is the only Living Spec target (`docs/ux/projects/UX-projects.md`). This restores its existing
behavior, so no capability, use-case, UX object-register or architecture change is intended. No alternative screen
or new interaction is selected; the unavailable-count tooltip and Refresh behavior already exist.

### Acceptance and verification

- **COUNT-01**: Given Projects inside a real shared counts context, when `OwedCountsStore.refresh` returns an API
  error, then the unavailable count tooltip names the existing API message. Add this regression Red before the fix.
- **COUNT-02**: Given a thrown failure or invalid response, when the read settles, then `Needs-you counts are unavailable` is
  available. A response with an invalid total stays unknown; existing per-kind/per-project filtering is unchanged.
  Initial loading has no failure reason; a successful later read clears it. A pending retry retains the previous
  settled state until its response is accepted.
- **COUNT-03**: Given a session change while a read is pending, when the older result arrives, then current counts
  and failure reason remain unchanged by that result. Cover both obsolete success and obsolete failure responses.
- **COUNT-04**: Given the shared store, when Projects renders or a refresh fails, then no duplicate Projects count
  request occurs and the shell/Attention keep their existing neutral unknown presentation.

Development first adds the failing shared-store tooltip regression to `ProjectsView.integration.test.ts`, using a
real `OwedCountsStore` provided through `OWED_COUNTS_CONTEXT` and a mocked API refusal. Assert the existing title
`Needs-you count unavailable: Database busy`, a neutral dash and exactly one shared counts request. Record Red
before production edits. Extend store coverage for the fixed fallback, invalid total, recovery, API-error precedence
and both obsolete-session outcomes. Keep shell integration checks for the neutral unknown accessible names and
request cadence. The unmodified Attention consumer continues to use only known counts.

Initialize the backend even for this UI-only change. Run focused store and Projects/shell integration tests,
`just lint`, `just check` and document/architecture rules in Development. Planning inspection is no claim that these
checks have run or that the fix is delivered.
The sibling `PROP-sidebar-overflow-cues` is behaviorally independent. Both may touch `AppShell.integration.test.ts`,
so serialize their Development writes, handoff and integration when that current scope overlaps.

### Non-goals

1. **Scope Excluded**: changing count polling cadence, throttling or the read itself.
2. **Scope Excluded**: sidebar group redesign, ordering or diagnostic disclosure behavior.
3. **Scope Excluded**: displaying failure reasons where a count is available, or changing shell/Attention presentation.
4. **Scope Excluded**: backend, typed API and sidebar overflow-cue changes.

## 4. Lifecycle & Retirement Criteria

The S bugfix direction is ready for Host review and `plan-accept`. This Planning turn grants no acceptance,
handoff or implementation authority. Retire the proposal through normal acceptance and handoff after review.
No PADR, milestone, inherited answer or open source feedback requires transfer. No product work is deferred beyond
COUNT-01 through COUNT-04. Source evidence remains inspection only until Development records Red and Green.
