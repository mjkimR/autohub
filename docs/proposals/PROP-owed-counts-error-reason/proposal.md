---
id: PROP-owed-counts-error-reason
title: Preserve shared owed-counts failure reasons
summary: "Restore the Projects Needs-you failure tooltip through the shared counts store while preserving neutral count presentation and the existing request cadence."
status: draft
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

## 2. Technical Spike Questions

- **Q1**: Keep the failure reason separate from loading inside the shared store, using the existing API error-message
  convention and bounded fallback messages for thrown failures or invalid responses. Settle the internal state shape
  without changing the shell and Attention's visible neutral presentation.
- **Q2**: Confirm that successful reads clear a stale reason and an older session's result cannot replace current
  state. Projects must reuse the shared request rather than issue an additional count read.

The outcome fixes the direction, so Planning effort is low. Shared reactive state and error/recovery compatibility
warrant medium Development effort and independent code review.

## 3. Proposed Design & Impact

1. Retain the last failure reason in `OwedCountsStore`, distinct from initial loading.
2. Use that reason for the unavailable Projects Needs-you tooltip, matching the existing fallback path.
3. Clear the reason after recovery. Preserve request cadence, session-generation fences and neutral shell/Attention
   presentation; an outage must not appear as zero or a known owed count.
4. Align `UX-projects` state wording and enforcing-test evidence with the restored shared-context contract.

### Acceptance and verification

- **COUNT-01**: Given Projects inside a real shared counts context, when `OwedCountsStore.refresh` returns an API
  error, then the unavailable count tooltip names the existing API message. Add this regression Red before the fix.
- **COUNT-02**: Given a thrown failure or invalid response, when the read settles, then a bounded fallback reason is
  available. Initial loading has no stale failure reason; a successful later read clears it.
- **COUNT-03**: Given a session change while a read is pending, when the older result arrives, then current counts
  and failure reason remain unchanged by that result.
- **COUNT-04**: Given the shared store, when Projects renders or a refresh fails, then no duplicate Projects count
  request occurs and the shell/Attention keep their existing neutral unknown presentation.

Run focused store and Projects/shell integration tests, `just lint`, `just check` and document rules in Development.
The sibling `PROP-sidebar-overflow-cues` is behaviorally independent. Both may touch `AppShell.integration.test.ts`,
so serialize their Development writes, handoff and integration when that current scope overlaps.

### Non-goals

1. **Scope Excluded**: changing count polling cadence, throttling or the read itself.
2. **Scope Excluded**: sidebar group redesign, ordering or diagnostic disclosure behavior.
3. **Scope Excluded**: displaying failure reasons where a count is available, or changing shell/Attention presentation.
4. **Scope Excluded**: backend, typed API and sidebar overflow-cue changes.

## 4. Lifecycle & Retirement Criteria

This is a queued S bugfix draft. The approved split does not accept this child or start Development.
Retire the draft through its normal acceptance and handoff after the child direction is reviewed. No PADR,
milestone, inherited answer or open source feedback requires transfer. Source evidence is inspection only.
