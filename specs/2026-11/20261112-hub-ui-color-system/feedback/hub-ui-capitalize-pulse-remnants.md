---
id: FB-hub-ui-capitalize-pulse-remnants
title: Replace remaining CSS capitalize labels and pulsing loading text in hub-ui
scope: repo
kind: suggestion
category: docs-mismatch
target: docs/steering/visual-style.md
origin: agent
severity: noise
recurring: false
status: open
created_at: 2026-11-13
---

# [FB-hub-ui-capitalize-pulse-remnants] Replace remaining CSS capitalize labels and pulsing loading text in hub-ui

Deferred work from `SPEC-hub-ui-color-system` (reconcile-check-01 finding 3).

## 2. Suggestion / Change Request (suggestion, change-request)

- **Current Procedure**: `docs/steering/visual-style.md` requires display-case labels written in code and no motion
  on live or routine indicators for new or changed labels and indicators. Existing hub-ui elements outside that
  Unit's changes still derive labels with CSS `capitalize` and pulse loading text with `animate-pulse`.
- **Proposed Procedure**: Map each remaining raw state or status value to a display-case label in code and replace
  `animate-pulse` loading text with static text or an icon, then drop the "new or changed" qualifier from the two
  steering rules.
- **Expected Benefit**: One consistent rule across hub-ui; acronyms keep their case and motion stays reserved.
- **Cost & Risk**: Touches several feature files and their integration tests where they assert text; low behavior
  risk.
- **Attempted**: Hypothesis. Restart when any listed file is next changed or in a hub-ui polish pass; acceptance:
  `rg "capitalize|animate-pulse" modules/hub-ui/src` outside `src/lib/components/ui/` finds nothing and
  `just test-ui` passes.

## Evidence

```text
capitalize: DashboardView.svelte (recent job badge), AppShell.svelte (user name), DecisionQuestion.svelte (question
state badge), ScheduleJobsView.svelte (job status badge), AttemptHistoryDialog.svelte (attempt badge),
ProjectConnectionCheckDialog.svelte (status text).
animate-pulse: RunDecisionsDialog.svelte and SddDecisionHistory.svelte loading text.
```
