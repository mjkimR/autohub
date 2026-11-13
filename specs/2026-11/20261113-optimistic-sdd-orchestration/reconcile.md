---
reconcile_id: REC-optimistic-sdd-orchestration
status: pending
targets:
- file: README.md
  resolution: modified
- file: docs/README.md
  resolution: modified
- file: docs/architecture/ARCH-02-constraints.md
  resolution: modified
- file: docs/architecture/ARCH-05-1-containers.md
  resolution: modified
- file: docs/architecture/ARCH-05-2-components.md
  resolution: modified
- file: docs/architecture/ARCH-06-execution.md
  resolution: modified
- file: docs/architecture/ARCH-07-deployment.md
  resolution: modified
- file: docs/architecture/ARCH-08-crosscutting-concepts.md
  resolution: modified
- file: docs/architecture/ARCH-10-quality-requirements.md
  resolution: modified
- file: docs/architecture/ARCH-11-risks-and-technical-debt.md
  resolution: modified
- file: docs/capabilities/README.md
  resolution: modified
- file: docs/capabilities/delivery/CAP-PR-agent-dispatch.md
  resolution: modified
- file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  resolution: modified
- file: docs/capabilities/delivery/CAP-PR-owed-items.md
  resolution: modified
- file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
  resolution: modified
- file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
  resolution: modified
- file: docs/capabilities/mcp/CAP-MCP-tool-access.md
  resolution: modified
- file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
  resolution: modified
- file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  resolution: modified
- file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
  resolution: modified
- file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  resolution: modified
- file: docs/capabilities/sdk/CAP-SDK-existing-pr-bridge.md
  resolution: modified
- file: docs/capabilities/sdk/CAP-SDK-task-flow-execution.md
  resolution: modified
- file: docs/decisions/2026-11/20261106-sdd-batch-ledger.md
  resolution: modified
- file: docs/decisions/2026-11/20261113-offline-source-build.md
  resolution: modified
- file: docs/decisions/2026-11/20261113-repository-locked-runtime.md
  resolution: modified
- file: docs/decisions/2026-11/20261113-repository-path-sources.md
  resolution: modified
- file: docs/development/README.md
  resolution: modified
- file: docs/development/testing.md
  resolution: modified
- file: docs/development/toolchain.md
  resolution: modified
- file: docs/materials/2026-11/20261113-optimistic-sdd-orchestration/verification.md
  resolution: modified
- file: docs/operations/README.md
  resolution: modified
- file: docs/operations/deployment-status.md
  resolution: modified
- file: docs/operations/execution-targets.md
  resolution: modified
- file: docs/operations/sdd-runtime.md
  resolution: modified
- file: docs/proposals/PROP-run-origin-links/proposal.md
  resolution: modified
- file: docs/proposals/PROP-run-origin-links/target-docs.md
  resolution: modified
- file: docs/proposals/PROP-updated-at-maintenance/proposal.md
  resolution: modified
- file: docs/roadmap/README.md
  resolution: modified
- file: docs/steering/glossary.md
  resolution: modified
- file: docs/steering/product.md
  resolution: modified
- file: docs/steering/ux-objects.md
  resolution: modified
- file: docs/usecases/README.md
  resolution: modified
- file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  resolution: modified
- file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  resolution: modified
- file: docs/usecases/sdd/UC-execute-sdd-batch.md
  resolution: modified
- file: docs/usecases/sdd/UC-preview-sdd-milestone.md
  resolution: modified
- file: docs/usecases/sdd/UC-start-sdd-activity.md
  resolution: modified
- file: docs/usecases/sdk/UC-resume-verified-pr.md
  resolution: modified
- file: docs/ux/README.md
  resolution: modified
- file: docs/ux/delivery/UX-attention.md
  resolution: modified
- file: docs/ux/delivery/UX-decision-inbox.md
  resolution: modified
- file: docs/ux/delivery/UX-enroll-pull-request.md
  resolution: modified
- file: docs/ux/delivery/UX-pipeline-runs.md
  resolution: modified
- file: docs/ux/delivery/UX-run-decisions.md
  resolution: modified
- file: docs/ux/delivery/UX-run-page.md
  resolution: modified
- file: docs/ux/projects/UX-project-detail.md
  resolution: modified
- file: docs/ux/repository/UX-repository.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-batch.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-claim-recovery.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-decision-history.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-execution.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-milestone-preview.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-proposals.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-run.md
  resolution: modified
- file: docs/ux/sdd/UX-sdd-workflow-request.md
  resolution: modified
- file: docs/proposals/PROP-updated-at-maintenance/target-docs.md
  resolution: waived
  rationale: The existing timestamp target blueprint remains valid for retained writes;
    the proposal narrows removed native examples without changing this blueprint.
---

# [REC-optimistic-sdd-orchestration] Repository-owned SDD execution reconciliation

## Implemented Contract Reflection

`ADR-repository-owned-sdd-execution` records the approved responsibility boundary.
`CAP-SDD-native-delivery`, `UC-start-sdd-activity` and
`UC-complete-sdd-workflow` describe optimistic Draft activity creation, repository-
owned setup/workflow and ordinary PR questions/CI. `CAP-PR-pull-request-delivery`
and `CAP-PR-operator-decisions` retain dispatch, current-head CI/merge and input
ownership. AC-01 through AC-07 map to their API/progression regressions.

`CAP-SDD-runtime-isolation`, `CAP-SDD-workflow-control`,
`CAP-SDK-existing-pr-bridge`, their affected use cases and former live UI
contracts state retirement and retained-history limits. AC-08 through AC-10 map
to migration, fencing, explicit reconciliation, bridge and historical lineage
checks. `UX-sdd-claim-recovery` includes inspected acknowledgment and exact retry;
`UX-sdd-proposals`, `UX-sdd-execution` and `UX-sdd-run` reflect the reviewed drafts.
`docs/steering/ux-objects.md` and the affected use-case interfaces agree.

`ARCH-02-constraints`, `ARCH-05-1-containers`, `ARCH-05-2-components`,
`ARCH-06-execution`, `ARCH-07-deployment` and the affected crosscutting/quality/risk
documents remove evaluator ownership and describe retained recovery guarantees.
Contributor/operations guidance removes serving runtime and bridge provisioning;
Auto Hub's own development tooling remains repository-owned. AC-11 covers the
image/scripts/CI boundary. AC-12 covers this reflection and the four superseded
runtime/path/build/batch ADRs; `ADR-sdd-development` remains accepted.

The initial target blueprint was extended to the actual reverse-reference impact:
ordinary delivery/decision/owed-item/SDK/MCP/repository contracts and UX,
architecture containers, current operations/indexes, and claim recovery. Every
changed current document is listed above. Necessary dated source/check evidence
is retained separately in `MAT-optimistic-sdd-boundary` and
`MAT-optimistic-sdd-verification`.

## Open Proposals and Deferred Work

The user authorized rejection of related open proposals. No dedicated open
runtime/evaluator proposal existed to reject. `PROP-run-origin-links` retains
independent origins and historical unit/batch addressing while dropping live
readiness/control assumptions. `PROP-updated-at-maintenance` retains independent
timestamp behavior and narrows obsolete native-write examples. Other open work
is independent. The unchanged timestamp blueprint is waived above with that
reason; no implementation guarantee is waived.

No required acceptance criterion is deferred. An alternative queue, remote
runner, replacement SDK bridge or Action for asset restoration is excluded by
the approved scope and is not a delivery promise. The Planning proposal was
promoted through handoff, with acceptance audit retained in this spec and its
original records preserved in Git.

## Verification Evidence

Fresh high-effort code review round 2 passed after fixing round 1's ownership,
recovery and type-check findings. The missing-number regression failed before
its fix and passes afterward. Full backend SQLite:1207 passed,25 skipped.
Broad PostgreSQL:235 passed; final affected PostgreSQL:30 passed. UI:547 passed.
Standalone SDK:27 passed and wheel/source builds. `just lint`, final
`just lint-check`, `just check`, document/CI rules and typed API freshness passed.
`MAT-optimistic-sdd-verification` separates these executed checks from source
inspection and unperformed live GitHub/provider/deployment verification.

## Entrypoints

Derived candidates were reviewed. Broad task directories, infrastructure,
test paths and deleted evaluator helpers were rejected: mechanical overlap does
not make them product entrypoints. Existing active doorways remain; dispatch and
operator-decision lists were bounded to three actor-facing entry files. Retired
runtime/workflow contracts point at API refusal/control doors, and the bridge
contract points at registration and receipt observation. Only those selected
pairs were applied through the entrypoint CLI; no broad directory was added.
The independent reconciliation envelope records final semantic verification.
