---
reconcile_id: REC-tick-continuation
status: resolved
targets:
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    resolution: modified
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/capabilities/sdk/CAP-SDK-task-flow-execution.md
    resolution: modified
  - file: docs/usecases/execution/UC-run-due-work.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
    resolution: modified
  - file: docs/usecases/sdk/UC-execute-task-flow.md
    resolution: modified
---

# Reconciliation: tick continuation

`CAP-SDK-task-flow-execution` and `UC-execute-task-flow` reflect bounded ready-step and same-ID recovery continuation with real wait boundaries.
`CAP-SDD-native-delivery` and `UC-start-sdd-activity` reflect prompt progression only after a claim is durably bound.
`CAP-PR-pull-request-delivery` and `UC-complete-sdd-workflow` reflect prompt explicit resume, replay suppression and shared project admission.
`CAP-EXEC-scheduling-maintenance` and `UC-run-due-work` reflect retained due-time cadence only for maintenance and project dispatch intervals.

No storage/API schema, domain terminology or architecture boundary changes. Existing Project-before-Run mutation order and durable attempt fencing remain in force.
Pipeline batch reordering was excluded at intake because evidence did not justify the concurrency complexity; it is not deferred required work.

Verification: source and test inspection are distinct from executed SQLite/PostgreSQL checks reported in the workflow envelopes. No live provider or deployment claim is made.

Entrypoint review retained feature doorway files. Mechanically suggested tests, helper paths and unrelated cross-feature candidates were excluded. Existing PR API entrypoints remain the public doorway for prompt resume.
