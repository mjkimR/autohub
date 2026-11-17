---
reconcile_id: REC-sdd-gate-question
status: resolved
targets:
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
    resolution: modified
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
    resolution: modified
formal_docs:
  design: "none: the change adds instruction text only; no stateful mechanism, identity or write order changes (DESIGN-sdd-activity-publication is untouched)"
  domain: "none: no domain record, relationship or term changes; gate questions are ordinary Run questions"
  operations: "none: no new symptom or owner route; a gate question appears in the existing decision inbox"
---

# Reconciliation: SDD gate questions

`CAP-SDD-native-delivery` rule 15 states the gate question instruction for SDD activity requests: raise a stopped
human gate through the attempt-bound marker after pushing, keep the marker's attempt and head, never infer the
decision, apply a resumed gate answer (including requested changes) and leave the PR Draft. It cites the three new
unit tests in `test_requests.py`. `pipeline_runs/requests.py` joins its entrypoints as the doorway where the
instruction is built.

`UC-complete-sdd-workflow` gains extension 3b (gate stop after push, answer and resume before Ready, Ready without
an applied answer stays the operator's choice) and acceptance example SDD-FOLLOW-05.

Unaffected, with reasons:

- `CAP-PR-operator-decisions`: question parsing, storage, discovery and resume rules are unchanged; AC-05 reuses
  them through the existing optimistic SDD integration test.
- `CAP-PR-pull-request-delivery` SDD activity context: still ordinary attempts, questions and explicit resume
  without stage selection or authored workflow decisions.
- `UX-sdd-run`, `UX-run-decisions`, `UX-decision-inbox`: no screen change; the gate question uses the existing
  question editor.
- `ADR-repository-owned-sdd-execution` and `ADR-remove-native-sdd-compatibility`: no decision changes; no typed
  route, schema or marker is added.
- Generated UI client: no API change.

Deferred: live observation of a Planning activity on the canary SDD repository after deployment (spec section 5).
It is evidence for the instruction's effect, not a contract gap.
