---
reconcile_id: REC-decision-notifications
status: resolved
targets:
  - file: docs/capabilities/notifications/CAP-NOTIFY-operator-notifications.md
    resolution: modified
  - file: docs/usecases/notifications/UC-configure-operator-notifications.md
    resolution: modified
  - file: docs/usecases/notifications/UC-receive-decision-notice.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/ux/settings/UX-notifications.md
    resolution: modified
  - file: docs/ux/settings/UX-decision-subscription.md
    resolution: modified
  - file: docs/ux/settings/UX-decision-notice-history.md
    resolution: modified
  - file: docs/ux/delivery/UX-decision-inbox.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/steering/glossary.md
    resolution: modified
  - file: docs/architecture/ARCH-06-execution.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
    resolution: modified
  - file: docs/usecases/access/UC-access-hub.md
    resolution: modified
  - file: docs/ux/access/UX-sign-in.md
    resolution: modified
  - file: docs/decisions/2026-11/20261106-decision-notice-delivery.md
    resolution: modified
---

# Reconciliation: `SPEC-decision-notifications`

All sixteen blueprint targets retain the selected separate-dialog design. The authorized promoted ADR changes only Confirmation. Native approval/control contracts remain with their existing owners; the notice navigation use case links those goals without restating their effects.

## Evidence

Source and enforcing tests were inspected separately from execution. Recorded execution: focused SQLite14 passed1skipped, PostgreSQL15 passed, relatedUI19 plus storage7 passed; final wording Google/storage13 passed. Previous full affected backend84/5skipped and UI273 passed before review fixes. Mandatory lint and check passed on the corrected source. No live external or deployment evidence.

Same-fixture baseline test test_disabled_subscription_baseline_then_one_matching_admission measured zero decision sends disabled and one admitted generation enabled; the base was not checked out.

No explicitly linked open feedback or concrete deferred deliverable remains in this scope. Live delivery and new channels are non-goals. A future polling-design reconsideration is conditional rationale, not an implementation handoff.

## Entrypoints and boundaries

Selected notification decision API, exact discovery UseCase and login component doorways. Generated types, tests, migrations, helpers and unrelated feature candidates were rejected as entrypoints. Existing owner UCs received navigation wording only and retain their doorways. Task boundary markup was normalized so the CLI reads the originally admitted notifications directory; no scope was added. The exact promoted ADR Confirmation path was separately admitted by the Host's initial payload and is included in Task3.

## Reconcile round1 fix batch

Original save revision, destination generation and settings are rendered as immutable fields. Original resend notice and attempt IDs are separate from current subscription/attempt observation. No raw payload dump is rendered. Missing selected-project rejection carries an owner-proven refusal code; generic404 remains uncertain. Approved bounds, timing, example link and sign-in/content disclosures appear before Save. The timing rule explicitly excludes reviewed resend, and the selector document describes the loaded first100 accessible choices.

Fail-before evidence: new component regressions failed for absent original save/resend details and settings disclosures; API regression failed on UNAVAILABLE rather than definitive refusal. After fixes, SQLite15 passed1skipped and notificationUI11 passed. Required type/build check passed.

## Final verification

Independent high reconcile round2 confirmed all five round1 findings resolved. Final source fb0fe74 has SQLite15 passed1skipped, PostgreSQL16 passed, notificationUI13 passed and auth13 passed. Both fresh-command stale-receipt regressions failed before their exact two-line fix and pass afterward. Mandatory lint, type checks and production build passed; final API regeneration produced no tracked drift. Only metadata and records follow this verified source.
