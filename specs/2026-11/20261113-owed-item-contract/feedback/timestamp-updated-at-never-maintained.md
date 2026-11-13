---
id: FB-timestamp-updated-at-never-maintained
title: TimestampMixin updated_at is never maintained on update
scope: unknown
kind: friction
category: docs-mismatch
target: app_layer_base TimestampMixin (updated_at server_onupdate) and owner models using it
origin: agent
severity: workaround
recurring: false
status: promoted
created_at: 2026-11-13
---

# [FB-timestamp-updated-at-never-maintained] TimestampMixin updated_at is never maintained on update

## 1. Friction / Question (friction, question)

- **Context**: Choosing `waiting_since` for owed items whose owners keep no state-entry time (Work Plans, Work Items,
  SDD batches, PR runs, replacement links).
- **Expectation**: `updated_at` reflects the last write, as its name and existing readers (run `finished_at` in
  `PipelineRunQueries.list_attempts`) assume.
- **Actual**: `TimestampMixin.updated_at` uses `server_onupdate=func.now()` with no trigger in the migrations, so
  ordinary ORM updates leave it at the insert time; no application code sets it either.
- **Workaround (or Interpretation Chosen)**: `SPEC-owed-item-contract` uses `updated_at` and states in its assumptions
  that Hub keeps no state-entry time; in practice it equals the creation time.
- **Suggestion**: Either maintain `updated_at` (an ORM `onupdate` or a database trigger) or stop reading it as a last
  write time; then owed waiting times and run finish times become accurate.

## Evidence

```text
app_layer_base/base/models/mixin.py: updated_at ... server_default=func.now(), server_onupdate=func.now()
rg "updated_at" in modules/hub/app: only flows/repos.py sets it explicitly; migrations define no update trigger.
```

- **Disposition**: PROP-updated-at-maintenance: bugfix proposal to maintain `updated_at` on every write to Hub-owned rows, with the affected models and readers surveyed.
