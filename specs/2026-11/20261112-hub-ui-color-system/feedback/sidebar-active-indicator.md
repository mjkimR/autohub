---
id: FB-sidebar-active-indicator
title: Strengthen the hub-ui sidebar active indicator
scope: repo
kind: suggestion
category: other
target: UX-app-shell
origin: agent
severity: noise
recurring: false
status: open
created_at: 2026-11-13
---

# [FB-sidebar-active-indicator] Strengthen the hub-ui sidebar active indicator

Deferred product work from `SPEC-hub-ui-color-system` (section 7, Follow-ups).

## 2. Suggestion / Change Request (suggestion, change-request)

- **Current Procedure**: The active sidebar item is distinguished by `aria-current`, `font-semibold` and foreground
  text contrast; its neutral `sidebar-accent` fill alone measures about 1.14:1 against the sidebar. The administrative
  links have no active style.
- **Proposed Procedure**: Give the active sidebar item a stronger non-color-only indicator and give the
  administrative links an active style, following `docs/steering/visual-style.md`, without spending attention
  color on navigation.
- **Expected Benefit**: Operators locate the current screen faster, in both themes.
- **Cost & Risk**: Touches `AppShell.svelte` and `UX-app-shell`; must not compete with attention marks.
- **Attempted**: Hypothesis; measured contrast recorded in `SPEC-hub-ui-color-system` section 6. Restart when the
  shell is next changed; acceptance: the active item and active administrative link are identifiable without color
  and the UI pair meets 3:1.

## Evidence

```text
SPEC-hub-ui-color-system section 6: the active sidebar item keeps aria-current, font-semibold and about 15:1 text
contrast (about 5.6:1 for inactive items); its sidebar-accent fill alone measures about 1.14:1.
Section 7 lists a stronger active indicator and an administrative-link active style as follow-ups outside the Unit.
```
