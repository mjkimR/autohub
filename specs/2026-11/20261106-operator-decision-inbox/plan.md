---
id: PLAN-operator-decision-inbox
spec: SPEC-operator-decision-inbox
---

# Technical Plan: `SPEC-operator-decision-inbox` Find pending delivery decisions across projects

## 1. Constitution & Invariant Review

No invariant change. `ADR-decision-inbox-read-projection` retains mutation authority with existing owners.

## 2. Architecture Overview & Impact
- Target Area: capabilities/delivery/
- Target Docs Blueprint: `PROP-operator-decision-inbox-target` (Living Spec targets for this plan and reconcile.md)

## 3. Component Breakdown & Interface Contracts

Pipeline-run discovery owns the rebuildable projection, cursor validation and listing. Native SDD supplies a pure candidate extractor from persisted owner evidence and a bounded exact-subject refresh adapter. Owner changes update discovery in the same transaction. The application shell links a Decisions screen which reuses the run decision dialog.

GET `/api/v1/pipeline-runs/decisions` accepts project ID, kind, ordinary question state, opaque cursor and limit (default 20, range 1–100). Return entries, has_more and next_cursor; malformed/filter-mismatched cursor returns 422. Review uses an exact entry key and generation; a stale or racing subject returns 409, inaccessible owner 404. Refresh performs no advance, publication or approval.

## 4. Storage & State Management

Store stable entry key, run/project owner, subject identity/fingerprint, kind, question state, title, revision, evidence basis, immutable generation waiting time and observation time. Index waiting time plus key, with project/kind filters. Cascade run deletion. Bootstrap supported persisted evidence in bounded migration batches. Native generation fingerprints include evidence head/base, runtime/policy, workflow, project binding and request content.

## 5. Error Handling & Edge Cases

Reuse current authentication and visibility policy. Join current run/project at list time. Preserve worker publication-pending rows as nonactionable; omit unsupported request kinds. CAS inspection against run revision, epoch and binding, preserving carry_decisions and all authority fences. On errors disable mutation and require explicit reinspection; never silently choose another request.

### Planned Boundaries:
- `modules/hub/migrations/versions/`
- `modules/hub/tests/integration/migrations/`
- `modules/hub-ui/src/lib/api/`
- `modules/hub/app/features/project_management/pipeline_runs/`
- `modules/hub/app/features/project_management/sdd/`
- `modules/hub/tests/integration/features/project_management/pipeline_runs/`
- `modules/hub/tests/integration/features/project_management/sdd/`
- `modules/hub-ui/src/lib/features/project-management/pipeline-runs/`
- `modules/hub-ui/src/lib/components/`
- `modules/hub-ui/src/routes/`
- `docs/capabilities/delivery/`
- `docs/capabilities/sdd/`
- `docs/usecases/delivery/`
- `docs/usecases/sdd/`
- `docs/ux/delivery/`
- `docs/ux/navigation/`
- `docs/steering/`
- `docs/architecture/`

### Excluded Boundaries:
- `docs/operations/`
- `.github/`
- `packages/sdk/`

## 6. Verification & Test Plan

Backend integration tests cover projection lifecycle, backfill, keyset boundaries, invalid cursors, exact selected requests and CAS races (AC-01–AC-07). PostgreSQL tests cover transactional visibility, lock races and indexed queries. UI tests cover screen filtering, pagination, owner routing, disabled refresh and focus restoration (AC-05–AC-08). Initialize backend, run affected tests and typed API generation, then `just lint` and `just check`. No quantitative performance improvement is claimed; compare navigation outcome with feature absent in the same fixture. Required high-effort code and reconcile reviews precede integration.
