---
id: PROP-decision-continuation
title: Follow decisions through explicit continuation
summary: "Connect reviewed decisions to explicit next actions and visible application outcomes without conflating saved answers, approval or resumption."
status: reviewing
created_at: 2026-11-05
target_area: capabilities/delivery/
priority: medium
size: M
planning_effort: high
dev_effort: high
milestone: MS-operator-decisions
depends_on:
  - PROP-operator-decision-inbox
boundaries:
  owns:
    - modules/hub-ui/src/lib/api/
    - modules/hub/app/features/project_management/pipeline_runs/
    - modules/hub/app/features/project_management/sdd/
    - modules/hub/tests/integration/features/project_management/pipeline_runs/
    - modules/hub/tests/integration/features/project_management/sdd/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - docs/capabilities/delivery/
    - docs/capabilities/sdd/
    - docs/usecases/delivery/
    - docs/usecases/sdd/
    - docs/ux/delivery/
    - docs/ux/sdd/
    - docs/steering/
  excludes:
    - docs/operations/
    - .github/
    - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-decision-continuation] Follow decisions through explicit continuation

## 1. Background & Hypothesis

Existing contracts intentionally separate saving an answer, applying it, publishing native decisions and authorizing integration. These distinctions protect authority, but completing a decision can leave the operator locating its next step elsewhere. Contextual continuation can make each transition visible and accessible without collapsing those operations.

### Source anchors

`CAP-PR-operator-decisions` requires explicit saved-answer selection for resume. `UX-sdd-workflow-request` states that a recorded worker answer remains open until its envelope is published. `PROP-operator-decision-inbox` supplies the common discovery and navigation entry point this work completes.

## 2. Technical Spike Questions

- **Q1**: Which saved, applied, publication-pending and delivery-pending states can existing owner receipts expose, and where is a read-model extension needed?
- **Q2**: Which next actions are valid for ordinary answers, proposal decisions, worker answers and integration authority without treating them as interchangeable?
- **Q3**: How should unknown outcomes, changed heads, later pauses and replayed requests appear while preserving stable mutation identities?

## 3. Proposed Design & Impact

- Extend the inbox review flow and existing decision surfaces with explicit saved/applied/publication/delivery outcomes and their valid next actions.
- Keep Save answer separate from Resume with selected answer. Keep native question publication distinct from recording a worker answer.
- Keep selected answer and review context available through refresh and recoverable failures; invalidate actionable stale context when authority changes.
- Reuse owner-specific request IDs and receipts. A replay must not undo a later stop or create a second application.
- Expose a direct route to the resulting run or pending native action after a decision.

### Candidate acceptance examples

These examples guide Planning; the accepted spec will settle the requirements.

- **E1**: Saving an ordinary answer leaves execution stopped and presents an explicit resume action for that saved answer.
- **E2**: A native worker answer recorded before envelope publication shows that remaining step without declaring the question resolved.
- **E3**: A changed head requires renewed inspection; a lost response can recover the existing receipt without a second application.
- **E4**: Replaying a successful continuation after a later pause leaves the run paused.

### Non-goals

- **Scope Excluded**: Implicit answer application, automatic approval, generic resume as native authority, replacing owner-specific APIs, batch approval and provider/SDK decision support.
- **Scope Excluded**: pilot operation, deployment, production verification,
  monitoring, incident detection and CI trigger changes.

## 4. Lifecycle & Retirement Criteria

User plan-intent authorizes this high-effort Planning turn. ORDER OVERRIDE: Planning may precede completion of `PROP-operator-decision-inbox`; this exception authorizes Planning only. The accepted inbox design is a provisional dependency, not implemented evidence. No plan-accept or Development handoff authority is supplied. Planning resolves the spike
questions, evaluates the recommended design and drafts affected interactions
before code. The milestone frames the theme without binding the final scope.

The direct prerequisite is `PROP-operator-decision-inbox`. It supplies the shared foundation described above. Eligibility requires its exact completed spec anchor after handoff; update the edge through the normal handoff reference process.

Acceptance and Development handoff follow `sdd-proposal`. Rejection retains
the decision and reason through the proposal lifecycle. This proposal is complete
only through a verified accepted implementation, not from creating this draft.
