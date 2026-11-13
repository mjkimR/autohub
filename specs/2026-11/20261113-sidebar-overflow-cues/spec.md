---
id: SPEC-sidebar-overflow-cues
title: Show sidebar navigation overflow cues
summary: Show decorative theme-token cues at navigation edges with hidden content so operators can discover off-screen links on short viewports.
status: planned
created: 2026-11-13
decomposed_from: PROP-hub-ui-shell-polish
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---
<!-- devkit:skeleton -->

# [SPEC-sidebar-overflow-cues] Show sidebar navigation overflow cues

## 1. Problem Statement & Motivation

Handed off from proposal PROP-sidebar-overflow-cues on 2026-11-13.
- **Preserved Materials**: `docs/materials/2026-11/20261113-sidebar-overflow-cues`
- Target Docs Blueprint: `PROP-sidebar-overflow-cues-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

`UX-app-shell` scrolls the active navigation link into view, but no edge signal shows that other links remain above
or below a short sidebar viewport. Decorative edge cues can expose that hidden content without changing navigation.

This feature is split from ~~`PROP-hub-ui-shell-polish`~~ at `d9cf2ae7ed792ecb8582c07d9f09979f544e26db`.
Inherited implementation and test inspection is retained in `docs/materials/2026-11/20261113-sidebar-overflow-cues/sidebar-evidence.md`. No browser or layout
verification has run. Medium Planning settles the cue treatment and responsive states before code; medium
Development verifies layout-dependent behavior and accessibility with independent review.

## 2. User Stories

- **US-1**: As a developer/agent, I want to implement Show sidebar navigation overflow cues so that system capabilities are extended.

## 3. Non-Goals

1. **Scope Excluded**: <what this change will not do>

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] <scenario>
- **Given** <precondition>
- **When** <action>
- **Then** <expected result>

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### 2. Planning Decisions

Source inspection at `7e780ab7e45757bdf44e6edd330767f62ffd41dc` confirms the existing desktop navigation scrollport, active-link scrolling and unbounded narrow Menu. No layout or browser test ran during Planning.

| Choice | Assessment |
| --- | --- |
| Edge shadow using existing sidebar tokens (selected) | A directional shadow indicates continuation without fading link text. Reserve small edge gutters outside the scrollport, so decoration never covers a link, active outline or focus ring. Verify visibility in both themes during Development. |
| Fade from the sidebar surface to transparent | A surface overlay is simple, but fading link content weakens readability. A fade confined to the same reserved gutters is viable, but provides less directional separation from the sidebar surface. |

Use a cohesive `SidebarNavViewport.svelte` wrapper in the existing shared component directory. It owns the bounded scrollport, inner content measurement and decorative edge gutters; it receives navigation content through a snippet. It does not own groups, routes, counts or active-link behavior. Keep `SidebarLink.svelte`'s `scrollIntoView({ block: 'nearest' })` behavior.

Measure on mount and scroll, and use `ResizeObserver` on both viewport and content to capture resize, System disclosure and administrative-link arrival. After the narrow Menu becomes visible and layout settles, scroll the displayed active link into view within the navigation scrollport, then measure its cues. A hidden active link in an explicitly collapsed System group stays hidden; preserve the existing disclosure choice and current-page mark. Hidden zero-height regions expose no cues. Clamp fractional edge comparisons with a documented one-CSS-pixel tolerance, and disconnect observers/listeners on unmount. Scrolling the active link triggers the same update path. The fallback when `ResizeObserver` is unavailable retains native scrolling and updates from scroll/window resize and known content/visibility changes.

The desktop sidebar remains viewport-bounded. Bound the open narrow Menu to the space remaining below its header, with a shrinking navigation region and reachable session controls. Observe the navigation viewport rather than creating another page scroll region. This is necessary for SCROLL-05: the current narrow aside grows with its contents and has no bounded navigation overflow. Opening and closing Menu preserves existing navigation semantics. Development covers loading a lower System or administrative destination while Menu is closed, then opening it: the visible active link must lie within the navigation scrollport without scrolling the surrounding page.

Use existing sidebar surface/ink tokens through `layout.css`; add a named semantic cue token only if needed to meet both-theme visibility. No arbitrary palette, new attention emphasis or new focus target is introduced. Exact gutter dimensions and opacity are implementation choices verified by real layout; the acceptance requirement is visible directional continuation without overlap or interaction interception. These are local presentation choices, so no PADR is needed.

### 3. Proposed Design & Impact

1. Show a top cue only when navigation content remains above and a bottom cue only when content remains below.
   Show neither when the navigation fits.
2. Recalculate after scroll, viewport or content changes. Keep cues decorative and hidden from assistive technology.
3. Preserve navigation order, System disclosure, keyboard access and active-link visibility.
4. Draft the changed `UX-app-shell` states before implementation and reflect the verified result in that owner.

#### Acceptance and verification

- **SCROLL-01**: Given fitting navigation, when the sidebar renders or resizes, then neither overflow cue appears.
- **SCROLL-02**: Given overflowing navigation, when positioned at the top, middle or bottom, then each cue indicates
  only content hidden beyond its edge.
- **SCROLL-03**: Given a resize, System expansion/collapse or administrative-link arrival, when layout settles, then
  cues reflect the resulting hidden content without requiring another user scroll.
- **SCROLL-04**: Given keyboard navigation or an active-link change, when the existing link scrolls into view, then
  links remain usable and cues neither obscure content nor intercept pointer/focus behavior.
- **SCROLL-05**: Given short desktop and narrow Menu layouts in both themes, when a real-layout browser check runs,
  then the correct cues are visible and decorative, the navigation scrolls within the available viewport, and Menu and session controls remain reachable. Mocked dimensions may supplement that evidence.

Use the established UI integration harness and a real browser layout check, followed by `just lint`, `just check`
and document rules. The sibling `SPEC-owed-counts-error-reason` is behaviorally independent; serialize Development
writes, handoff and integration when their `AppShell.integration.test.ts` scope overlaps.

#### Non-goals

1. **Scope Excluded**: changing count polling cadence, throttling or the count read itself.
2. **Scope Excluded**: sidebar groups, their order or collapsed diagnostic-group behavior.
3. **Scope Excluded**: counts error-reason display or any changes to the shared counts store and Projects.
4. **Scope Excluded**: backend, typed API and unrelated shell redesign.

### 4. Lifecycle & Retirement Criteria

This S feature is under Planning review. Direction acceptance and Development handoff remain Host/user actions. The selected shadow treatment and screen delta are retained in `target-docs.md`; Development proves the layout outcomes.
No PADR, milestone, inherited answer or open source feedback requires transfer. Source evidence is inspection only.

