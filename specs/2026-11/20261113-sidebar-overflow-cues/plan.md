---
id: PLAN-sidebar-overflow-cues
spec: SPEC-sidebar-overflow-cues
---

# Technical Plan: `SPEC-sidebar-overflow-cues`

## 1. Constitution & Invariant Review

No architecture, capability, use-case, permission or accepted-decision change. The only Living Spec target is `UX-app-shell`, describing this navigation presentation. Source premises match the accepted handoff. No ADR or new UX object is needed.

## 2. Architecture Overview & Impact

`SidebarNavViewport.svelte` owns viewport/content measurement, reserved shadow gutters and bounded active-link alignment. `AppShell.svelte` supplies menu visibility and current destination and keeps group, count and session ownership. `SidebarLink.svelte` retains existing active-link behavior. Semantic CSS in layout.css colors shadows with existing sidebar tokens and bounds the narrow aside below its header.

## 3. Component & Interface Design

The wrapper receives children, visible Menu state and current destination; its navigation retains the Primary navigation accessible name. A one-CSS-pixel tolerance suppresses fractional rounding artifacts. ResizeObserver observes the viewport and content; MutationObserver supplies content fallback. A settled reveal aligns only the displayed current link by adjusting navigation scrollTop, preserving page scroll and manual System collapse.

## 4. Storage & State Management

Edge booleans and element references are local component state. No persistence or request is added. Existing System storage and route-bound Menu choice remain authoritative.

## 5. Error Handling & Edge Cases

Hidden zero-height lists have no cues. No ResizeObserver falls back to window resize, scroll and content observation. Cleanup disconnects observers and removes resize listeners. Gutters reserve space whether cues show, avoiding measurement loops.

## 6. Verification & Test Plan

Focused SidebarNavViewport/AppShell integration tests prove AC-01 through AC-04 and observer cleanup. An ignored local browser harness renders authored shell components and CSS for AC-03 through AC-05 at short desktop and narrow sizes in both themes. Record actual dimensions, edge states, active/focus bounds and page scroll. Run just lint, just check, document/CI rules and independent code review; reconcile UX-app-shell after implementation. No deployed-process e2e or live backend behavior is claimed.
