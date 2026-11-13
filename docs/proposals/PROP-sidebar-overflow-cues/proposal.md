---
id: PROP-sidebar-overflow-cues
title: Show sidebar navigation overflow cues
summary: "Show decorative theme-token cues at navigation edges with hidden content so operators can discover off-screen links on short viewports."
status: draft
created_at: 2026-11-13
target_area: ux/navigation/
priority: low
size: S
planning_effort: medium
dev_effort: medium
boundaries:
  owns:
    - ux/navigation/
    - modules/hub-ui/src/lib/components/shared/
    - modules/hub-ui/src/routes/layout.css
  excludes:
    - docs/decisions/
    - modules/hub/
    - modules/hub-ui/src/lib/api/
    - modules/hub-ui/src/lib/features/attention/
    - modules/hub-ui/src/lib/features/project-management/projects/
task_kind: feature
decomposed_from: PROP-hub-ui-shell-polish
workflow: sdd-proposal
---

# [PROP-sidebar-overflow-cues] Show sidebar navigation overflow cues

## 1. Background & Hypothesis

`UX-app-shell` scrolls the active navigation link into view, but no edge signal shows that other links remain above
or below a short sidebar viewport. Decorative edge cues can expose that hidden content without changing navigation.

This feature is split from ~~`PROP-hub-ui-shell-polish`~~ at `d9cf2ae7ed792ecb8582c07d9f09979f544e26db`.
Inherited implementation and test inspection is retained in `materials/sidebar-evidence.md`. No browser or layout
verification has run. Medium Planning settles the cue treatment and responsive states before code; medium
Development verifies layout-dependent behavior and accessibility with independent review.

## 2. Technical Spike Questions

- **Q1**: Compare a fade and a shadow at the overflowing edge using existing theme tokens. Choose a treatment that
  remains visible in both themes without obscuring links, adding a focus target or intercepting interaction.
- **Q2**: Determine the smallest component responsibility for measuring hidden content and updating on scrolling,
  resize, System expansion/collapse and administrative-link arrival. Preserve existing active-link scrolling.

## 3. Proposed Design & Impact

1. Show a top cue only when navigation content remains above and a bottom cue only when content remains below.
   Show neither when the navigation fits.
2. Recalculate after scroll, viewport or content changes. Keep cues decorative and hidden from assistive technology.
3. Preserve navigation order, System disclosure, keyboard access and active-link visibility.
4. Draft the changed `UX-app-shell` states before implementation and reflect the verified result in that owner.

### Acceptance and verification

- **SCROLL-01**: Given fitting navigation, when the sidebar renders or resizes, then neither overflow cue appears.
- **SCROLL-02**: Given overflowing navigation, when positioned at the top, middle or bottom, then each cue indicates
  only content hidden beyond its edge.
- **SCROLL-03**: Given a resize, System expansion/collapse or administrative-link arrival, when layout settles, then
  cues reflect the resulting hidden content without requiring another user scroll.
- **SCROLL-04**: Given keyboard navigation or an active-link change, when the existing link scrolls into view, then
  links remain usable and cues neither obscure content nor intercept pointer/focus behavior.
- **SCROLL-05**: Given short desktop and narrow Menu layouts in both themes, when a real-layout browser check runs,
  then the correct cues are visible and decorative. Mocked dimensions may supplement that evidence.

Use the established UI integration harness and a real browser layout check, followed by `just lint`, `just check`
and document rules. The sibling `PROP-owed-counts-error-reason` is behaviorally independent; serialize Development
writes, handoff and integration when their `AppShell.integration.test.ts` scope overlaps.

### Non-goals

1. **Scope Excluded**: changing count polling cadence, throttling or the count read itself.
2. **Scope Excluded**: sidebar groups, their order or collapsed diagnostic-group behavior.
3. **Scope Excluded**: counts error-reason display or any changes to the shared counts store and Projects.
4. **Scope Excluded**: backend, typed API and unrelated shell redesign.

## 4. Lifecycle & Retirement Criteria

This is a queued S feature draft. The approved split creates the child without direction acceptance or Development
handoff. Planning compares cue treatments, drafts the relevant states and runs its mandatory Challenger pass.
No PADR, milestone, inherited answer or open source feedback requires transfer. Source evidence is inspection only.
