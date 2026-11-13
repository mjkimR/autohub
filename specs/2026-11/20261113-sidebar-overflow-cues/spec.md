---
id: SPEC-sidebar-overflow-cues
title: Show sidebar navigation overflow cues
summary: "Expose hidden navigation beyond each scroll edge with decorative theme-token shadows while keeping desktop and narrow Menu destinations and controls reachable."
status: in-progress
created: 2026-11-13
decomposed_from: PROP-hub-ui-shell-polish
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-sidebar-overflow-cues] Show sidebar navigation overflow cues

## 1. Problem Statement & Motivation

Operators cannot tell whether more navigation links exist beyond a short sidebar viewport. `UX-app-shell` already scrolls the active destination into view. This change exposes remaining links with decorative shadows and gives the open narrow Menu a viewport-bounded list.

## 2. User Stories

- As an operator, I want to discover off-screen destinations without losing the current destination, keyboard access or session controls.

## 3. Non-Goals

1. **Scope Excluded**: navigation group order, System disclosure policy, route ownership and count polling or presentation changes.
2. **Scope Excluded**: backend, API, SDK, new interaction targets and unrelated shell redesign.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] Fitting and edge states
- **Given** fitting or overflowing navigation
- **When** the list renders or scrolls to its top, middle or bottom
- **Then** only edges with more than one CSS pixel of hidden content show a decorative shadow; fitting and zero-height hidden lists show neither.

### [AC-02] Layout changes and lifecycle
- **Given** a mounted navigation viewport
- **When** it resizes, System changes, administrative links arrive or its content changes
- **Then** edge state updates without another scroll; unsupported ResizeObserver retains scroll, resize and content updates, and unmount disconnects observers and listeners.

### [AC-03] Active destination on reveal
- **Given** a lower System or administrative destination loaded with narrow Menu closed
- **When** Menu opens and visible layout settles
- **Then** the displayed active link is inside the navigation scrollport before cues settle, without moving the surrounding page; an explicitly collapsed System remains collapsed.

### [AC-04] Decoration and keyboard access
- **Given** navigation in either theme
- **When** the operator focuses or activates a link
- **Then** shadows occupy reserved gutters outside link, active-outline and focus-ring content; they have no accessibility node, focus stop or pointer interception, and existing links and disclosure remain usable.

### [AC-05] Bounded responsive layout
- **Given** short desktop and narrow viewports in light and dark themes
- **When** actual browser layout renders the sidebar or opens Menu
- **Then** navigation scrolls within available height, appropriate cues are visible, and Menu and session controls remain reachable.

## 5. Screens

The approved screen delta remains in `PROP-sidebar-overflow-cues-target`. The overall arrangement is unchanged; selected edge shadows use reserved gutters instead of fading link content. Planning's Challenger reveal gap was resolved and its optional UX review passed. Development preserves that direction and verifies real layout.
