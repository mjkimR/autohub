---
reconcile_id: REC-run-origin-links
status: resolved
targets:
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
    resolution: modified
  - file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
    resolution: modified
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
    resolution: modified
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
    resolution: modified
  - file: docs/usecases/sdd/UC-execute-sdd-batch.md
    resolution: modified
  - file: docs/ux/delivery/UX-run-page.md
    resolution: modified
  - file: docs/ux/delivery/UX-pipeline-runs.md
    resolution: modified
  - file: docs/ux/delivery/UX-attention.md
    resolution: modified
  - file: docs/ux/repository/UX-repository.md
    resolution: modified
  - file: docs/ux/sdd/UX-sdd-batch.md
    resolution: modified
  - file: docs/steering/ux-objects.md
    resolution: modified
---

# Reconciliation: Run origin links and subject deep links

The bounded run-origin read changes CAP-PR-pull-request-delivery and its delivery use case and screens. Addressed unit/ref validation changes CAP-DOC-repository-viewer, its use case and Repository panel. Exact old batch selection changes CAP-SDD-native-delivery and its retained-history use case/panel. The existing UX object register gains only representation wording.

No architecture or ADR changes: reads remain on caller sessions, existing project-management dependencies are reused and repository agents retain execution ownership. No schema, enrollment, retention, control or provider effect changes.

The inherited target blueprint cited step4 of the retired batch use case. Current UC-execute-sdd-batch has three retained-history steps; reflection uses steps1–3 and never restores retired workflow authority.

Source feedback FB-attention-sdd-batch-deep-link is terminal promoted and remains unchanged for traceability. Its exact-address scope is implemented and verified by the origin link and Repository regressions. No required scope is deferred, and no separate deferred product work was identified.

Verification evidence is in the review/reverify and final report envelopes. Document test pointers describe enforcing coverage; no live provider, deployed-service or browser walkthrough evidence is claimed.

Entrypoint derivation produced broad directory, generated-client, helper and test candidates; these are rejected because they are not document doorways. Existing capability and ordinary-delivery/repository use-case entrypoints already identify the API/UI entry surfaces. Only UC-execute-sdd-batch gains its exact SDD API and SddBatch component doorways.

Independent reconciliation verified every target and AC01–09. Its P3 table-continuity finding was repaired and self-verified by checking contiguous interaction rows; no contract or source change was needed.
