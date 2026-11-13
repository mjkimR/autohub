---
id: PROP-optimistic-sdd-orchestration-target
title: Repository-owned SDD execution Living Spec targets
summary: "Plan optimistic activity dispatch, retire live SDD evaluation and bridge contracts, and retain historical native execution evidence."
status: draft
proposal: SPEC-optimistic-sdd-orchestration
created_at: 2026-11-13
targets:
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
  - file: docs/capabilities/sdk/CAP-SDK-existing-pr-bridge.md
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  - file: docs/capabilities/mcp/CAP-MCP-tool-access.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  - file: docs/usecases/sdd/UC-execute-sdd-batch.md
  - file: docs/usecases/sdd/UC-preview-sdd-milestone.md
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
  - file: docs/ux/sdd/UX-sdd-batch.md
  - file: docs/ux/sdd/UX-sdd-decision-history.md
  - file: docs/ux/sdd/UX-sdd-execution.md
  - file: docs/ux/sdd/UX-sdd-milestone-preview.md
  - file: docs/ux/sdd/UX-sdd-proposals.md
  - file: docs/ux/sdd/UX-sdd-run.md
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
  - file: docs/architecture/ARCH-02-constraints.md
  - file: docs/architecture/ARCH-05-2-components.md
  - file: docs/architecture/ARCH-06-execution.md
  - file: docs/architecture/ARCH-07-deployment.md
  - file: docs/architecture/ARCH-08-crosscutting-concepts.md
  - file: docs/architecture/ARCH-10-quality-requirements.md
  - file: docs/architecture/ARCH-11-risks-and-technical-debt.md
  - file: docs/operations/sdd-runtime.md
  - file: docs/operations/execution-targets.md
  - file: docs/development/testing.md
  - file: docs/development/toolchain.md
  - file: docs/steering/product.md
  - file: docs/steering/glossary.md
  - file: docs/steering/ux-objects.md
  - file: docs/decisions/2026-11/20261113-repository-locked-runtime.md
  - file: docs/decisions/2026-11/20261113-repository-path-sources.md
  - file: docs/decisions/2026-11/20261113-offline-source-build.md
  - file: docs/decisions/2026-11/20261106-sdd-batch-ledger.md
  - file: docs/proposals/PROP-run-origin-links/proposal.md
  - file: docs/proposals/PROP-run-origin-links/target-docs.md
  - file: docs/proposals/PROP-updated-at-maintenance/proposal.md
  - file: docs/proposals/PROP-updated-at-maintenance/target-docs.md
---

# [PROP-optimistic-sdd-orchestration-target] Repository-owned SDD execution Living Spec targets

This blueprint is conditional on `SPEC-optimistic-sdd-orchestration`; it does not
change the implemented guarantees before Development lands.

## 1. Capabilities and Use Cases

- Rewrite `CAP-SDD-native-delivery` and `UC-start-sdd-activity` for explicit intent,
  Draft PR creation and ordinary PR ownership. State that status, size, dependency,
  policy, lock and bundle readiness are repository/agent responsibilities.
- Rewrite `UC-complete-sdd-workflow` as work through the ordinary PR lifecycle.
  Link durable questions and GitHub CI to their existing owners.
- Retire the live guarantees of `CAP-SDD-runtime-isolation`,
  `CAP-SDD-workflow-control` and `CAP-SDK-existing-pr-bridge`. Keep their IDs as
  historical/retirement contracts where needed for retained reads and references.
  Rewrite `UC-decide-sdd-proposal`, `UC-preview-sdd-milestone` and
  `UC-execute-sdd-batch` to state the discontinued operations and retained history;
  no alternative live workflow is promised.
- Align `CAP-PR-pull-request-delivery`, `CAP-PR-operator-decisions` and
  `CAP-MCP-tool-access` with generic execution, questions, current-head CI and the
  retired mutations. Add reciprocal capability/use-case links where ownership moves.
- Resolve reverse references in `docs/materials/2026-11/20261113-optimistic-sdd-orchestration/reverse-references.txt`. Additional
  active contract references found by Development are reconciliation targets;
  completed specs remain historical evidence.

## 2. Existing UI Surfaces

Remove runtime/readiness probes, native stage/request controls, milestone execution
preview and live batch selection/controls from the existing repository and Run
surfaces. Reuse existing ordinary Run controls and question UI. Preserve unit/run
links and exact historical batch/decision reads with a visible retired label.
No replacement panel, new queue or evaluator screen is proposed.

Rewrite `UX-sdd-execution`, `UX-sdd-proposals` and `UX-sdd-run` around these retained
controls. `UX-sdd-milestone-preview`, `UX-sdd-batch` and
`UX-sdd-workflow-request` describe their retired execution controls and history
where still exposed. `UX-sdd-decision-history` remains read-only history. Match
literal labels and owning use-case steps after implementation.

## 3. Architecture and Decisions

`ARCH-02-constraints` removes runtime/sandbox admission requirements.
`ARCH-05-2-components` removes evaluator and publication ownership.
`ARCH-06-execution` defines optimistic activity metadata, old authority fencing,
question/head ordering and the retained-history boundary.
`ARCH-07-deployment` removes evaluator image stages, cache/build/sandbox/source
credentials and documents the smaller serving dependency boundary.
`ARCH-08-crosscutting-concepts`, `ARCH-10-quality-requirements` and
`ARCH-11-risks-and-technical-debt` stop promising runtime compatibility or native
stage guarantees. They retain ordinary PR ownership/recovery guarantees.

Promote `ADR-repository-owned-sdd-execution` at handoff. When the implementation
and restating contracts agree, mark `ADR-repository-locked-runtime`,
`ADR-repository-path-sources`, `ADR-offline-source-build` and
`ADR-sdd-batch-ledger` superseded by that ADR. Preserve `ADR-sdd-development`.

## 4. Operations, Contributor Tooling and Open Proposals

Replace the obsolete runtime/bridge installation procedures with retirement and
ordinary PR/CI guidance in the existing operations guides. Document that local
cancellation does not cancel externally dispatched agent work. Remove the
isolated evaluator test recipes/job and source credential from contributor
guidance. Keep Auto Hub's own `just init hub`, devkit and project checks.

Update glossary/product/UX register entries to reflect descriptive SDD activity
context and historical native evidence. Do not rename unrelated SDK runtime
concepts or claim that ordinary GitHub CI proves repository-internal workflow.

Keep `PROP-run-origin-links` and `PROP-updated-at-maintenance` as independent
outcomes. Reconcile their native SDD assumptions with historical-only subjects
under exclusive proposal ownership; preserve their existing source feedback and
accepted direction. No open dedicated evaluator proposal was found to reject.

## 5. Before and After

| Responsibility | Before | After |
| --- | --- | --- |
| Repository environment/assets | Hub lock install, cache, build and sync | Repository and working agent |
| Repository workflow | Hub evaluated stages, holds and publication | Repository and working agent |
| Work delivery | Stage-specific native PR attempts | Existing PR attempts with activity intent |
| Operator input | Native requests plus Run questions | Existing Run questions and explicit resume |
| Verification | Hub final rules plus GitHub CI | Repository-owned GitHub Actions observed by Hub |
| Milestone/batch execution | Hub graph and sequential native admission | Retired; retained history remains inspectable |
| SDK built-in bridge | Hub checkout evaluation before PR resume | Retired; generic SDK and scoped PR APIs remain |
