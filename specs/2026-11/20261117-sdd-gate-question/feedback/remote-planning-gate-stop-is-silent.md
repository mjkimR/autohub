---
id: FB-remote-planning-gate-stop-is-silent
title: Remote Planning runs stop at plan-accept without surfacing the gate to their host channel
scope: upstream
kind: suggestion
category: missing-capability
target: devkit sdd-proposal workflow and the spec skill's planning guidance
origin: agent
severity: workaround
recurring: false
status: open
created_at: 2026-11-17
---

# [FB-remote-planning-gate-stop-is-silent] Remote Planning runs stop at plan-accept without surfacing the gate to their host channel

## 2. Suggestion / Change Request (suggestion, change-request)

- **Current state**: The Planning use case assumes a local Host that presents the review, asks for `plan-accept`,
  records it and integrates the branch. A one-shot remote agent (a cloud Codex task dispatched by an orchestrator)
  completed Planning on `plan-<slug>`, set the proposal to `reviewing`, recorded "reached the plan-accept gate" in its
  worker envelope and ended its reply. It used no question channel its orchestrator offered, so the orchestrator
  saw only a Draft PR waiting for Ready. Merging that PR would land a `reviewing` proposal without
  `gate:plan-accept`, and the later handoff refuses with `SPEC_HANDOFF_NOT_READY`.
- **Proposed change**: When a Planning (or any) run has no interactive Host and stops at a human gate, the workflow
  guidance should tell the agent to raise the gate through the host-provided question channel, including the
  `devkit spec proposal report` summary, and on a relayed answer to record it with `--by user` before integration.
- **Rationale**: Auto Hub now instructs this repository-neutrally (`CAP-SDD-native-delivery` rule 15), but the
  repository's own workflow guidance is the authority the agent follows; aligning it removes reliance on the
  orchestrator's wording.
