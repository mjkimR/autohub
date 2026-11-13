---
reconcile_id: REC-updated-at-maintenance
status: pending
targets:
  - file: docs/capabilities/delivery/CAP-PR-owed-items.md
    resolution: modified
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
    resolution: modified
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
    resolution: modified
---

# Timestamp maintenance reconciliation

`CAP-PR-owed-items` preserves owner-last-write fallback and clock precedence, and names real owner-write regressions.
`CAP-EXEC-scheduling-maintenance` states mapped update maintenance, pure bookkeeping exceptions, observation release rotation and prospective historical-row behavior.
`CAP-WORK-work-plan-execution` retains its retention window and explains Plan/Item/replacement clocks and enforcing tests.

The accepted contracts keep their actor goals, HTTP fields and UI actions, so no use-case or UX document changes.
The repair changes no schema, dependency pin, transaction ownership or architectural invariant and requires no ADR.
The Host authorized exact adjacent SDD acknowledgment and ordinary resume refresh repairs after SQLite replay regressions exposed identity-map versus persisted serialization differences.
These preserve existing response consistency and add no timestamp representation redesign.

Source feedback `FB-timestamp-updated-at-never-maintained` remains terminal `promoted` and is retained unchanged for traceability.
The implementation and Red/Green tests address its transferred scope; the inherited sole-writer claim was corrected in the accepted inventory.
No required or concrete deferred product work remains.

Entrypoints retain existing capability doorway files: the timestamp helper is not a new actor entrypoint.
Actual check execution and source identity live in the envelopes; these document test links do not claim live deployment.
