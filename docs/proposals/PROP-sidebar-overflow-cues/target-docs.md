---
id: PROP-sidebar-overflow-cues-target
title: Sidebar overflow cue screen delta
summary: "Draft directional navigation overflow cues and bounded narrow Menu states for the authenticated navigation panel."
status: draft
proposal: PROP-sidebar-overflow-cues
created_at: 2026-11-13
targets:
  - file: docs/ux/navigation/UX-app-shell.md
---

# Sidebar overflow cue screen delta

## Document targets

Update `UX-app-shell` Content, States, Interactions and Evidence with the verified overflow behavior. Keep existing navigation groups, labels, counts, System disclosure and active-link behavior. No capability or use case guarantee changes. `UC-access-hub` steps 2 and 3 continue to reach the shell; navigation remains a global control. The UX object register needs no additional object or call to action because cues decorate existing navigation.

## Screens

### `UX-app-shell` delta

- **Element**: panel.
- **Use cases**: `UC-access-hub`.
- **Purpose**: Navigate the management console within an admitted Browser session. Off-screen destinations are disclosed by edge cues; the selected destination remains primary within navigation.
- **Content**: Existing Browser session context, navigation groups and controls remain. The navigation list sits between its existing brand and session-control regions. A subtle shadow in a reserved top or bottom edge gutter appears only when navigation content remains beyond that edge. The gutters do not cover link text, active outlines or keyboard focus rings. Cues use the sidebar visual roles from `docs/steering/visual-style.md`, are hidden from assistive technology and add no focus stop or pointer interception. Both wide sidebar and open narrow Menu bound the list to available height; Menu/header and session controls remain reachable. Native scrollbar, wheel/touch and keyboard navigation remain available.
- **Content tree**: Browser session navigation context → existing grouped destination links → conditional top/bottom decorative continuation; existing session/health/theme controls remain below the list. No group ordering or action changes.
- **States**: `navigation-fits` shows no cues; `navigation-top` shows only the bottom cue; `navigation-middle` shows both cues; `navigation-bottom` shows only the top cue. Each state permits normal scrolling and destination selection. `menu-closed` shows no hidden-region cue; reopening Menu waits for visible layout, scrolls its displayed active destination into the navigation scrollport, then recomputes edges. An explicitly collapsed System group remains collapsed with its existing current-page mark. These states coexist with existing populated, System, owed and offline states.

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Scroll navigation | global: discover off-screen destinations | navigation-top, navigation-middle, navigation-bottom | navigation-top, navigation-middle, navigation-bottom | | | Only edges with remaining hidden content show continuation. |
| Resize viewport, toggle System or receive administrative links | global: keep navigation discoverable after layout changes | navigation-fits, navigation-top, navigation-middle, navigation-bottom | navigation-fits, navigation-top, navigation-middle, navigation-bottom | | | Cues reflect settled layout without another scroll. |
| Open Menu | global: reveal narrow navigation | menu-closed | navigation-fits, navigation-top, navigation-middle, navigation-bottom | | | The bounded list appears, its displayed active link scrolls into view, and cues then reflect its position; session controls remain reachable. |
| Close Menu | global: return to current screen | navigation-fits, navigation-top, navigation-middle, navigation-bottom | menu-closed | close | | Navigation collapses through its existing control. |
| Keyboard focus or active-destination change | global: reach a destination | navigation-fits, navigation-top, navigation-middle, navigation-bottom | navigation-fits, navigation-top, navigation-middle, navigation-bottom | | | Existing active-link scrolling remains; focus and active outlines remain unobscured. |
| Select Projects | global: leave shell navigation for a management screen | navigation-fits, navigation-top, navigation-middle, navigation-bottom | populated | `UX-projects` | | Existing destination opens and route-bound narrow Menu closes. |

The overall panel arrangement is unchanged, so no competing primary-region layout is open. Fade and shadow treatment alternatives are compared in the proposal.

## Verification targets

Development adds deterministic integration coverage for fitting and top/middle/bottom boundaries, fractional-scroll tolerance, resize, disclosure, administrative-link arrival, hidden-to-visible Menu and observer cleanup. Existing route, keyboard, counts and System tests remain. A real browser checks light/dark themes in short desktop and narrow Menu layouts, including text, focus/active outlines, scrollability, reachable Menu/session controls and no pointer interception. Include direct loading of a lower System or administrative destination with Menu closed, then opening it and checking active-link bounds without surrounding-page scroll. Record actual viewport sizes and inspected states in the Development evidence. No such browser result is claimed by this draft.
