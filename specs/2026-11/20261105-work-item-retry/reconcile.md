---
reconcile_id: REC-work-item-retry
status: pending
targets:
  - file: docs/capabilities/work-plans/CAP-WORK-work-plan-execution.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    resolution: modified
  - file: docs/usecases/work-plans/UC-execute-work-plan.md
    resolution: modified
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
    resolution: modified
  - file: docs/ux/work-plans/UX-work-plans.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/architecture/ARCH-06-execution.md
    resolution: modified
  - file: docs/decisions/2026-11/20261105-work-item-recovery-lineage.md
    resolution: modified
  - file: docs/materials/2026-11/20261105-work-item-retry/development-checks.md
    resolution: modified
---

# Recovery contract reconciliation

`SPEC-work-item-retry` retains original Item/Run lineage, exact request identity, guarded admission and prior outcome history under `ADR-work-item-recovery-lineage`. No required scope is deferred or waived.

`CAP-WORK-work-plan-execution` rules29–36 and its recovery interface cover AC-01, AC-03–09, AC-11 and AC-12. `CAP-PR-pull-request-delivery` rules23–26 cover retained terminal identity, budgets, owner races and pushed-head adoption (AC-02, AC-09, AC-10). The use cases fold recovery into their original actor goals; `UX-work-plans` retains the inline disclosure and explicit acceptance/hold/reconciliation/running/refusal feedback. The Work Item register row extends its existing representation.

`ARCH-06-execution` reflects typed records/events, the shared lock order, durable intent and lease fencing. The accepted ADR changes only its confirmation and restatement pointers. The material records actual check execution separately from source inspection and live deployment.

The three-Item disabled/enabled fixture compares one head without checking out base: predecessor equality, preserved second-Item identity, Run counts and merge-only successor release. The terminal fixture separately verifies epoch equality and delivery counts. No performance claim is made.

Inbound capability/ADR references were inspected. Existing PR dispatch, CI, normal resume and merge contracts retain their original owners. No additional feature dependency edge or SDK/operations change is introduced. Planning UX awaiting-admission feedback is retained; implementation UI regressions include the current hold detail after remount.

Entrypoint derivation was reviewed. The delivery use case adds the actual Work Plan API doorway. Existing capability/Work Plan doorway files remain; broad feature directories, generated API folders, models, migrations and test mirrors were rejected as doorway candidates because they are implementation scope rather than entrypoints.
