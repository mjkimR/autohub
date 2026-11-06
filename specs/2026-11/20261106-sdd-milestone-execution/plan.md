---
id: PLAN-sdd-milestone-execution
spec: SPEC-sdd-milestone-execution
---

# Technical Plan: `SPEC-sdd-milestone-execution`

## 1. Architecture Overview & Impact

Retain `ADR-sdd-batch-ledger`: SDD owns durable intent and checkpoints; the existing native activity and PR owners retain gate, execution and merge authority. The landed `SPEC-sdd-milestone-readiness` provides bounded exact catalog resolution and observed admission. Preserve its eligible-only ephemeral selection; a separate execution selection admits supported dependency-held future intent.

## 2. Component Breakdown & Interface Contracts

- SDD batch models and additive migration retain immutable ordered membership, creation request digest/actor, project/repository/connector/config basis, member content and graph fingerprints, current evaluation and stable phase claims. Project then Batch locks serialize claims and controls. One unresolved batch excludes a second.
- Strict create/read/control API delegates through a use case, service and repository. Creation independently recomputes the complete pinned preview; request/actor replay returns current retained state. Revision controls only affect future claims.
- The coordinator evaluates fresh exact dependencies, content/config drift and owner-confirmed merge/validated handoff lineage before one bounded transition. Missing canonical PROP repair remains a hold; ledger lineage cannot satisfy another dependency. A stopped batch retains an unsettled claim.
- Shared project/unit/activity reservations and a pinned expected-base ActivityStarter seam serialize batch and individual starts. Durable remote checkpoints recover the same branch/PR/run after uncertainty; markers alone never authorize ownership.
- Existing maintenance drives bounded fair batch observations/admissions. Retention excludes unresolved linked runs until durable settlement. No native run control or PR executor is added.
- Repository components expose execution selection, immutable confirmation, effective preferences, durable progress and future-admission controls. Preserve request identity across uncertainty and ignore older revisions/project responses.

## 3. Verification & Test Plan

Initialize backend with `just init hub`. Add SQLite and PostgreSQL multi-connection tests for request/control/claim fencing, exact selection limits and zero-effects refusal, phase/merge/lineage gating, base/content/policy drift, branch/PR/enrollment crash checkpoints and retention. Add UI selection/control/conflict/reload tests. Regenerate API with `just gen-ui-api`; run focused suites, `just lint`, `just check`, cumulative rules and generated freshness. Independent high code review and reconciliation are mandatory.

Before/after counts use the same head with batch driver disabled versus enabled. No timing claim or live deployment claim is made. Screens and all twelve Living Spec targets remain in `PROP-sdd-milestone-execution-target`.
