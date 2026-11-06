---
reconcile_id: REC-operator-decision-inbox
status: resolved
targets:
  - file: docs/decisions/2026-11/20261106-decision-inbox-read-projection.md
    resolution: modified
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
    resolution: modified
  - file: docs/ux/delivery/UX-decision-inbox.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
  - file: docs/ux/delivery/UX-run-decisions.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-run.md
    resolution: modified
  - file: docs/ux/navigation/UX-app-shell.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
  - file: docs/architecture/ARCH-05-2-components.md
    resolution: modified
---

# Reconciliation: decision discovery

The projection and exact owner review implement AC-01–AC-08. Discovery has no mutation authority; owner controls and revocation guards retain their contracts. The dedicated screen, exact routing and focus restoration replace manual cross-project discovery. No quantitative improvement is claimed or measured.

Inspected tests are named in the owning contracts. Executed checks: backend owner/migration SQLite 241 passed with 39 isolated CLI cases skipped; final discovery/migration PostgreSQL 10 passed, followed by 9 changed-listing PostgreSQL tests; UI 235 passed; repository types/build passed. Final lint/lint-check and types/production build passed. An ignored PostgreSQL probe captured the actual listing query, verified its limit-plus-one bound and inspected its normal and indexed-compatible plans; indexed-path compatibility used seqscan disabled only within the disposable probe. No timing claim is made. No live deployment evidence is claimed.

No in-scope work is deferred. Decision-outcome continuation remains the independently accepted PROP-decision-continuation and is not implemented here. Source proposal UX findings are reflected in the retained screen and object register.
