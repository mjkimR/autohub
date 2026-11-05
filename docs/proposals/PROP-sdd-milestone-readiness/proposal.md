---
id: PROP-sdd-milestone-readiness
title: Preview executable SDD milestone work
summary: "Expose selected milestone members and authoritative readiness so operators can review a sequential execution selection without starting work."
status: draft
created_at: 2026-11-05
target_area: capabilities/sdd/
priority: high
size: M
planning_effort: medium
dev_effort: high
milestone: MS-native-sdd-execution
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/app/features/project_management/repositories/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub/tests/unit/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/repositories/
    - docs/capabilities/repository/
    - docs/capabilities/sdd/
    - docs/usecases/repository/
    - docs/usecases/sdd/
    - docs/ux/repository/
    - docs/ux/sdd/
    - docs/steering/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-sdd-milestone-readiness] Preview executable SDD milestone work

## 1. Background & Hypothesis

`CAP-DOC-repository-viewer` displays branch-specific milestone members, and `CAP-SDD-native-delivery` exposes individual native activity admission. There is no Hub-owned preview that resolves a milestone selection into inspectable executable activities. A read-only readiness contract can establish the selection basis before sequential execution is added.

### Source anchors

`modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts` covers selected-branch member navigation. `modules/hub/app/features/project_management/sdd/activities.py` owns individual start admission. Neither read-only milestone navigation nor a displayed document is execution authority.

## 2. Technical Spike Questions

- **Q1**: How will milestone membership, archived anchors and exact proposal/spec prerequisites be resolved against an identified repository revision?
- **Q2**: How will Planning, handoff-first Development, existing activities and blocked members be projected without duplicating devkit workflow rules?
- **Q3**: What limits and partial/truncated-result disclosures make a preview safe to use as a batch selection basis?

## 3. Proposed Design & Impact

- Expose a read-only Hub preview of milestone membership, selected repository identity, unit readiness and explicit hold/refusal reasons.
- Delegate workflow eligibility to the reviewed devkit runtime and reuse existing project-scoped activity lookup.
- Let operators choose an explicit subset and inspect recommended sequential order. Treat this selection as a hypothesis until execution admission re-evaluates it.
- Keep the embedded viewer read-only; place selection and readiness controls in a Hub-owned native execution surface.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: Previewing a milestone creates no activity branch, PR or Run.
- **E2**: A member with a missing or unfinished prerequisite exposes its exact hold rather than being selected as executable.
- **E3**: Changing the browse branch yields that branch's membership and repository identity; incomplete results disclose their limits.

### Non-goals

- **Scope Excluded**: Starting batches, durable execution queues, automatic approvals, inferred dependencies, modifying the vendored viewer and Work Plan binding.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

This is queued draft work in `MS-native-sdd-execution`. Creation does not start Planning,
accept the design or authorize implementation. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
