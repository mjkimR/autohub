---
id: FB-shell-pending-decision-count
title: Light the hub-ui shell from a global pending-decision count
scope: repo
kind: suggestion
category: missing-capability
target: UX-app-shell
origin: agent
severity: noise
recurring: false
status: open
created_at: 2026-11-13
---

# [FB-shell-pending-decision-count] Light the hub-ui shell from a global pending-decision count

Deferred product work from `SPEC-hub-ui-color-system` (Non-Goal 1 and section 7, Follow-ups).

## 2. Suggestion / Change Request (suggestion, change-request)

- **Current Procedure**: Attention appears only on badges, the dashboard Needs-you tile and Decisions inbox row
  rules. The shell shows no pending-decision signal because no global pending-decision count source exists; the
  Needs-you tile counts failed, paused and blocked PR runs, not pending decisions.
- **Proposed Procedure**: Once an API exposes a global pending-decision count, add an attention rule at the top of
  the application shell and a pending-count badge on the Decisions navigation item.
- **Expected Benefit**: Operators see owed decisions from any screen, not only from the inbox.
- **Cost & Risk**: Needs a backend count source and API change; a constantly lit shell risks alarm fatigue.
- **Attempted**: Hypothesis. Restart when a global pending-decision count source exists; acceptance: the shell
  signal appears only while the count is above zero, carries a text count, and links to `UX-decision-inbox`.

## Evidence

```text
SPEC-hub-ui-color-system Non-Goal 1 excludes shell lighting and any global pending-decision count;
When to Reconsider: when a global pending-decision count source exists for the shell.
```
