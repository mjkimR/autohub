---
reconcile_id: REC-owed-counts-error-reason
status: pending
targets:
  - file: docs/ux/projects/UX-projects.md
    resolution: modified
---

# Counts failure tooltip reconciliation

`UX-projects` now describes both shared and fallback failure tooltips, initial shared loading, pending retry and successful recovery. Its enforcing-check evidence includes the real-store dual-tooltip regression and focused store lifecycle tests. The existing Content promise is restored, not broadened.

`CAP-PR-owed-items` count membership and API contract remain unchanged. No actor goal, layout, navigation, shell/Attention presentation, domain vocabulary, architecture or ADR changes. No new entrypoint belongs on a capability or use case for this existing tooltip repair. There is no deferred product work and no source feedback assigned to this Unit.

Executed Development evidence is recorded in the Unit envelopes: one intended Red failure before source edits, focused Vitest54 passed, full lint and full type/build checks passed. These results do not establish live deployment or a real browser walkthrough.
