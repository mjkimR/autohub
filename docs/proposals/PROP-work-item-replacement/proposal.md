---
id: PROP-work-item-replacement
title: Link replacement work to original Work Items
summary: "Record explicit replacement relationships and dependency satisfaction decisions without rewriting original Work Plan outcomes."
status: draft
created_at: 2026-11-05
target_area: capabilities/work-plans/
priority: high
size: L
planning_effort: high
dev_effort: high
milestone: MS-batch-recovery
depends_on:
  - SPEC-work-item-retry
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/work_plans/
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

# [PROP-work-item-replacement] Link replacement work to original Work Items

## 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` supports replacement registrations through descriptive links and optional branch attachment. It has no structured replacement relationship, and replacement completion does not satisfy the original dependencies. Explicit operator-selected replacement evidence can remove manual graph reconstruction without falsifying the original outcome.

### Source anchors

`modules/hub/tests/integration/features/project_management/work_plans/test_registration.py::test_replacement_keeps_canceled_evidence_and_does_not_release_old_dependents` enforces the existing boundary. This is a feature proposal to extend that contract, not a claim that the existing behavior is defective.

## 2. Technical Spike Questions

- **Q1**: How will a replacement identify the exact original Work Item and accepted scope without introducing a general cross-Plan Item dependency graph?
- **Q2**: Which original and replacement outcomes, repository/target identities and revisions permit an explicit dependency-satisfaction decision?
- **Q3**: How will replacement chains, competing replacements, revocation and downstream completion be bounded and explained?

## 3. Proposed Design & Impact

- Reuse the recovery history and attempt identity established by `SPEC-work-item-retry`; replacement resolves work that cannot use ordinary in-place recovery.
- Record a structured original-to-replacement relationship with actor, reason and reviewed revisions. Keep execution evidence on its actual owner.
- Separate linking replacement work from accepting its confirmed result for explicitly identified downstream dependencies.
- Preserve the original failed, canceled or revoked outcome. Prevent silent graph-wide successor substitution and cycles.
- Present original work, replacement work and dependency-satisfaction decisions together on the Work Plan surface.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: Linking a replacement alone leaves the original dependent work held. An explicit valid satisfaction decision after the replacement merges releases only the reviewed dependency.
- **E2**: A replacement merged into another repository or target branch does not satisfy the original dependency.
- **E3**: A competing or cyclic replacement decision is refused without losing original or replacement history.

### Non-goals

- **Scope Excluded**: Automatic semantic equivalence, automatic successor substitution, general cross-Plan Item edges, rewriting revoked Plans as completed and re-executing successful original work.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

This is queued draft work in `MS-batch-recovery`. Creation does not start Planning,
accept the design or authorize implementation. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

The direct prerequisite is `SPEC-work-item-retry`. It supplies the shared foundation described above. Eligibility requires its exact completed spec anchor after handoff; update the edge through the normal handoff reference process.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
