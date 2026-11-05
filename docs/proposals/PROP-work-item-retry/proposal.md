---
id: PROP-work-item-retry
title: Retry failed Work Items
summary: "Recover eligible failed Work Items while preserving successful work, prior execution evidence and external request identities."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/work-plans/
priority: high
size: L
planning_effort: high
dev_effort: high
milestone: MS-batch-recovery
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/work_plans/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/migrations/
    - modules/hub/tests/integration/migrations/
    - modules/hub/tests/integration/features/project_management/work_plans/
    - modules/hub/tests/unit/features/project_management/
    - modules/hub-ui/src/lib/features/project-management/work-plans/
    - docs/capabilities/work-plans/
    - docs/usecases/work-plans/
    - docs/ux/work-plans/
    - docs/steering/
    - docs/architecture/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-work-item-retry] Retry failed Work Items

## 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` retains failed preparation and delivery outcomes but exposes no failed-Item retry API. Operators reconstruct work through another registration even when successful predecessors should remain untouched. A revision-checked recovery operation can let the original Work Plan finish while preserving its failed attempts.

### Source anchors

`modules/hub/app/features/project_management/work_plans/execution.py` records `preparation_failed`; `api.py` exposes Plan controls without an Item recovery command. `test_registration.py` covers replacement registration and preservation of the original outcome. These are inspected anchors, not a new test execution.

## 2. Technical Spike Questions

- **Q1**: Which preparation, failed, canceled and attention outcomes are eligible for recovery, and when is a new PR run required?
- **Q2**: How will prior linked runs and recovery attempts remain queryable without resetting attempt budgets or overwriting Item outcome evidence?
- **Q3**: How will an uncertain PR/comment effect be reconciled before recovery, and which revision, lease and capacity checks fence competing recovery requests?

## 3. Proposed Design & Impact

- Add an explicit Item recovery request with revision checks, authenticated actor, reason and idempotent request identity.
- Keep completed predecessor Items unchanged. Preserve prior execution links and identify each subsequent recovery attempt.
- Reconcile an existing owned branch/PR before preparing more work; retain unresolved external outcomes rather than treating them as permission to redispatch.
- Expose eligible recovery and refusal reasons on the existing Work Item surface. Reuse the PR execution owner for implementation, CI and merging.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: A three-Item chain fails at its second Item. Recovering that Item leaves the first Item's successful execution unchanged and releases the third only after confirmed success.
- **E2**: Replaying the same recovery request creates no second recovery attempt or external request; conflicting content under that identity is refused.
- **E3**: A stale revision or an uncertain external effect prevents a fresh dispatch and preserves the evidence needed for reconciliation.

### Non-goals

- **Scope Excluded**: Replacement dependency substitution, automatic retries of every failure, native SDD orchestration, rollback of remote effects and resetting exhausted execution budgets.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

This is queued draft work in `MS-batch-recovery`. Creation does not start Planning,
accept the design or authorize implementation. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
