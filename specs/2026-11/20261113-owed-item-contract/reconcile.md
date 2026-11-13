---
reconcile_id: REC-owed-item-contract
status: pending
targets:
  - file: docs/capabilities/README.md
    resolution: modified
  - file: docs/capabilities/agents/CAP-AGENT-catalog-admission.md
    resolution: modified
  - file: docs/capabilities/connections/CAP-CONN-connection-verification.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-owed-items.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    resolution: modified
  - file: docs/capabilities/notifications/CAP-NOTIFY-operator-notifications.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
    resolution: modified
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/steering/visual-style.md
    resolution: modified
  - file: docs/usecases/connections/UC-verify-project-connection.md
    resolution: modified
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/usecases/sdd/UC-execute-sdd-batch.md
    resolution: modified
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
    resolution: modified
  - file: docs/ux/navigation/UX-app-shell.md
    resolution: modified
  - file: docs/ux/operations/UX-dashboard.md
    resolution: modified
---

# Reconcile: `SPEC-owed-item-contract`

- `CAP-PR-owed-items` is new and owns the owed-item model, kinds, suppression, the list and counts reads and the
  per-run pending-decision flag; `docs/capabilities/README.md` lists it with the PR delivery contracts.
- Each owning capability states the predicate that makes its object owed (`CAP-PR-operator-decisions`,
  `CAP-PR-pull-request-delivery`, `CAP-WORK-work-plan-execution`, `CAP-SDD-workflow-control`,
  `CAP-CONN-connection-verification`); `CAP-AGENT-catalog-admission` states that a catalog hold is context only, and
  `CAP-NOTIFY-operator-notifications` states that notices are not the owed count.
- The five use cases served by `CAP-PR-owed-items` list it reciprocally and name the owed item in their postconditions.
- `UX-app-shell` and `UX-dashboard` record the owed count as the future source of the Badge and Needs-you tile, with no
  screen change; the glossary, the UX object register and the Attention definition in `visual-style.md` use the owed
  set.
- No architecture document changes: `ADR-owed-items-aggregate-read` already records the aggregate read, and
  `RULE-app-router-repo-import` still holds.

## Deferred work

- The Phase 2 Attention landing switches the shell Badge and the dashboard Needs-you tile to the owed count
  (spec Non-goal 4); it is outside this unit by the user's Planning decision.
- Run origin fields stay with `PROP-run-origin-links` (Non-goal 6).

## Source feedback

None carried.
