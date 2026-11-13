---
id: PROP-updated-at-maintenance-target
title: Living Spec targets for maintained owner timestamps
summary: "Clarify last-write timestamp semantics and enforcing regression evidence without introducing state-entry clocks or historical backfill."
status: draft
proposal: PROP-updated-at-maintenance
created_at: 2026-11-13
targets:
  - file: docs/capabilities/delivery/CAP-PR-owed-items.md
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
---

# [Blueprint] Maintained owner timestamps

This is a Planning draft, not an implemented contract.

- `CAP-PR-owed-items`: keep the owner-row last-write fallback and no state-entry guarantee. State that an existing
  run observation release can advance this clock. Add real owner-write regressions for each timestamp-backed kind.
- `CAP-EXEC-scheduling-maintenance`: retain the run-age rule and observation rotation. Explain that maintained
  timestamps apply prospectively; existing stored historical times are not reconstructed. Add a real late-cancel
  retention regression and bounded-observation fairness coverage.
- `CAP-WORK-work-plan-execution`: retain last-update semantics and retention windows. Link enforcing tests that
  update a Plan/Item through its owner and verify the corresponding owed/retention read.

No API field, actor goal, screen, state-entry column or persisted-data backfill is introduced.
