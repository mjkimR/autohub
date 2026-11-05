---
id: PROP-operator-decision-inbox
title: Find pending delivery decisions across projects
summary: "Aggregate actionable PR questions and native SDD decisions with links to current owner-specific review and decision surfaces."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/delivery/
priority: medium
size: L
planning_effort: medium
dev_effort: high
milestone: MS-operator-decisions
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/tests/integration/features/project_management/pipeline_runs/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - modules/hub-ui/src/lib/components/
    - modules/hub-ui/src/routes/
    - docs/capabilities/delivery/
    - docs/capabilities/sdd/
    - docs/usecases/delivery/
    - docs/usecases/sdd/
    - docs/ux/delivery/
    - docs/ux/navigation/
    - docs/steering/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-operator-decision-inbox] Find pending delivery decisions across projects

## 1. Background & Hypothesis

`CAP-PR-operator-decisions`, `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` expose different question and approval subjects through run-specific surfaces. Operators must locate the relevant project/run before deciding. A cross-project decision worklist can provide one entry point while leaving each mutation with its owner.

### Source anchors

`modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.svelte`, `SddWorkflowRequests.svelte` and `SddRunPanel.svelte` provide the existing owner-specific decision surfaces. `UX-run-decisions` and `UX-sdd-workflow-request` describe their distinct meanings.

## 2. Technical Spike Questions

- **Q1**: Which persisted ordinary questions, proposal decisions, workflow requests and integration approvals are actionable, and how are expired or superseded entries removed?
- **Q2**: How can filters, stable pagination and waiting age be implemented without unbounded per-run repository evaluation?
- **Q3**: How will inbox navigation resolve an exact owner/request and refresh its current revision and evidence before enabling actions?

## 3. Proposed Design & Impact

- Provide a paginated, filterable worklist across accessible projects for pending ordinary questions and native SDD decisions.
- Retain explicit decision kind, owning project/run/request, waiting age and inspected evidence identity. Distinguish answer saved from answer applied.
- Open the existing owner-specific review surface from a worklist entry and refresh its authoritative context before mutation.
- Treat the worklist as a read projection; do not create a generic approval command or a second authorization ledger.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: Ordinary question and native integration approval entries remain distinguishable and open their corresponding review controls.
- **E2**: An answered but unapplied ordinary question remains discoverable; an applied or superseded request is no longer offered as pending.
- **E3**: Opening an entry changed since listing refreshes or removes it before the operator can decide.
- **E4**: Filtering and pagination preserve project boundaries and do not start execution.

### Non-goals

- **Scope Excluded**: Health dashboards, incident detection, quota queues, bulk approvals, SDK machine approvals, Jules provider questions and account approval.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

This is queued draft work in `MS-operator-decisions`. Creation does not start Planning,
accept the design or authorize implementation. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
