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
status: resolved
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

## Disposition

Resolved on branch `uiux-label-motion-cleanup` (hub-ui follow-up outside SDD, by explicit user instruction).

- Labels: `modules/hub-ui/src/lib/labels.ts` adds `displayLabel`, a written label map lookup with a sentence-case
  fallback. Schedule job status (`ScheduleJobsView`, `DashboardView` recent jobs) shares
  `features/scheduling/schedule-jobs/presentation.ts`; attempt and question states use `attemptStateLabel` and
  `questionStateLabel` in `features/project-management/pipeline-runs/presentation.ts`; the connection check status
  maps `VerificationStatus` in `ProjectConnectionCheckDialog`. Underlying API values are unchanged.
- Motion: `RunDecisionsDialog` and `SddDecisionHistory` loading text no longer pulses; the attempt history and
  schedule config loading placeholders drop their spinning icon and read as static `role="status"` text. A spinning
  icon remains only on a busy Refresh control.
- `docs/steering/visual-style.md` states both rules generally, without the "new or changed" qualifier.
- Verification: `just test-ui` passed (54 files, 414 tests, including new `labels.test.ts` and presentation tests),
  `just lint` and `just check` passed.
- Remaining outside this branch: `AppShell.svelte` still renders the signed-in user's name with `capitalize`; that
  file is owned by a parallel branch and was not touched here. Drop the class there (or reopen this record) so
  `rg "capitalize|animate-pulse" modules/hub-ui/src` outside `src/lib/components/ui/` finds nothing.
