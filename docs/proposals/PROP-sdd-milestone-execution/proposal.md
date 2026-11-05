---
id: PROP-sdd-milestone-execution
title: Execute selected SDD milestone work sequentially
summary: "Progress a durable selection of native SDD units sequentially while preserving dependency checks, approval boundaries and recoverable controls."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/sdd/
priority: high
size: L
planning_effort: high
dev_effort: high
milestone: MS-native-sdd-execution
depends_on:
  - PROP-sdd-milestone-readiness
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/app/features/execution/tasks/domains/maintenance/
    - modules/hub/migrations/
    - modules/hub/tests/integration/migrations/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub/tests/unit/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/repositories/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - docs/capabilities/sdd/
    - docs/capabilities/execution/
    - docs/usecases/sdd/
    - docs/ux/sdd/
    - docs/steering/
    - docs/architecture/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-sdd-milestone-execution] Execute selected SDD milestone work sequentially

## 1. Background & Hypothesis

Native SDD activities are individually admitted, while milestone batch execution is outside `CAP-SDD-native-delivery`. Work Plans cannot provide this path because native SDD needs bound repository units. A durable sequential coordinator can connect the selection from `PROP-sdd-milestone-readiness` to existing native activity owners.

### Source anchors

`modules/hub/app/features/project_management/work_plans/execution.py::WorkPlanExecution.prepare` retains SDD work in `attention` when no spec is bound. `modules/hub/app/features/project_management/sdd/activities.py` and `progress.py` provide existing native activity admission and progression.

## 2. Technical Spike Questions

- **Q1**: What immutable selection and repository identity should a batch retain, and how should membership or dependency changes affect its remaining work?
- **Q2**: What confirms completion of Planning versus Development, and when may handoff-first Development start under current approval gates?
- **Q3**: How will one-active-unit progression, response-loss recovery and pause/stop race with native admission and PR completion?

## 3. Proposed Design & Impact

- Persist an explicit selected batch with request identity, revisioned controls and links to its existing native activities.
- Advance one selected unit at a time through eligible Planning and Development activities. Re-evaluate dependencies, workflow, runtime and project policy before every start.
- Wait at existing human decision boundaries and for the owning PR's confirmed outcome. Preserve current activity/PR ownership and reuse existing activity markers during recovery.
- Pause or stop future admission without silently canceling already admitted work. Resume from recorded identities after reconciliation.
- Show selected, active, held, completed and stopped work in a Hub-owned batch surface. Keep repository proposal/spec content authoritative.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: A dependent unit starts only after its prerequisite is authoritatively satisfied and all current start gates permit it.
- **E2**: A crash after PR creation recovers the same activity rather than creating another branch, PR or Run.
- **E3**: Pause winning before admission prevents the next start; already admitted work retains its own controls. Resume does not approve an outstanding decision.
- **E4**: Membership, head or runtime drift is visible and re-evaluated before subsequent admission.

### Non-goals

- **Scope Excluded**: Parallel execution, a second CI/merge controller, implicit approval of future gates, specification copies in Work Plans, SDK flow reuse and automatic failure replacement.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

This is queued draft work in `MS-native-sdd-execution`. Creation does not start Planning,
accept the design or authorize implementation. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

The direct prerequisite is `PROP-sdd-milestone-readiness`. It supplies the shared foundation described above. Eligibility requires its exact completed spec anchor after handoff; update the edge through the normal handoff reference process.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
