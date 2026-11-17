---
id: PLAN-sdd-gate-question
spec: SPEC-sdd-gate-question
---

# Technical Plan: `SPEC-sdd-gate-question` Surface repository workflow gates through the question channel

## 1. Constitution & Invariant Review

None requires an ADR. `ADR-repository-owned-sdd-execution` says Hub uses durable questions, answers and explicit
resume and "does not select stages or author repository workflow decisions". The change keeps that boundary: Hub
asks the agent to surface any stop that needs a human decision and relays the operator's own answer. It reads no
workflow state, names no gate and refuses no Ready status or merge (`CAP-SDD-native-delivery` rules 2, 5 and 8 are
unchanged). `ADR-remove-native-sdd-compatibility` removed typed native decision routes; this change adds no typed
route, schema or marker, so it does not revisit that decision.

## 2. Architecture Overview & Impact

- `modules/hub/app/features/project_management/pipeline_runs/requests.py`: the SDD branch of the instruction text
  gains a gate paragraph (AC-01, AC-02, AC-04). The non-SDD text is untouched (AC-03).
- `modules/hub/app/features/project_management/pipeline_runs/dispatch.py`: unchanged. The generic "stop before
  pushing" sentence stays for non-SDD runs, where a question after a push is not honored (the head check in
  `ObserveImplementation.observe` moves a non-optimistic Run to `awaiting_ci` before questions are read). The SDD
  instruction states the exception explicitly.
- `usecases/control.py` resume: unchanged. It appends the operator decision to the prior instructions, so the gate
  paragraph and the answer reach the resumed attempt together (AC-02).
- Question ingestion, storage, discovery and resume (`CAP-PR-operator-decisions`): unchanged; AC-05 reuses them.
- No new dependency, storage, migration, API, generated client or UI change.

## 3. Component & Interface Design

Normative instruction content for an SDD Run (wording may be tightened; the listed obligations are the contract and
the tests assert their key phrases):

```text
If the repository workflow stops at a human approval or decision gate (for example, accepting a reviewed plan),
first push the completed work, then raise the gate through the question marker below in your final reply.
In this activity a question raised after pushing completed work remains valid;
keep the marker's attempt and head values exactly as given, even after you push.
The question must let the operator decide without opening another tool: state the decision requested,
a short review summary (outcome, open questions, notable findings and checks) and the expected answers:
accept, request changes (with the changes), or reject (with the reason).
Never record or infer the operator's decision yourself before an answer arrives.
When a resumed request carries an operator decision that answers such a gate, apply it as the operator's decision
under the repository workflow, including requested changes to the reviewed work, which are within scope;
ask again only when the answer is ambiguous. Then run the required checks, push the result and leave the PR Draft.
```

The marker sentence exists because `parse_question` binds the marker to the dispatched head; an agent that writes
the pushed head would be silently ignored. The in-scope sentence exists because resume appends a generic "if it
changes acceptance criteria, stop and ask again" suffix (`usecases/control.py`), which would otherwise loop on a
"request changes" gate answer.

The text names no tool, command, gate ID or stage (AC-02), so it stays repository-neutral.

Living Spec owners (applied at `spec-sync`):

| Statement | Owner | Action |
| --- | --- | --- |
| SDD activity instructions ask for a gate question after pushing completed work and relay the answer as the operator's decision | `CAP-SDD-native-delivery` (new business rule) | add rule with `requests.py` tests as check |
| Gate stop as a question; answer and resume before Ready; Ready without an applied answer is the operator's choice, not a Hub refusal | `UC-complete-sdd-workflow` | add extension 3b and an acceptance example |
| Ordinary question/answer/resume contract | `CAP-PR-operator-decisions` | unaffected: no rule changes; listed as related only |
| SDD activity context in `CAP-PR-pull-request-delivery` | unaffected: still "ordinary questions, explicit resume, no stage selection" |
| `UX-sdd-run` | unaffected: the existing question editor shows the gate question; no new element |

Design, domain and operations: unaffected. No mechanism with state or identity is introduced (design), no domain
record or relationship changes (domain), and no new symptom routes to a different owner (operations); a gate
question is observed through the existing decision inbox.

## 4. Error Handling & Edge Cases

- The agent ignores the instruction and stops silently: the behavior is today's (Draft wait). Hub cannot detect it;
  live observation is the evidence boundary.
- The agent emits the marker without pushing: the existing pre-push question path applies unchanged.
- The agent changes the head after the question: existing head-specific application refuses a stale resume (`409`).
- The operator marks Ready without answering: Hub follows ordinary merge policy; the repository workflow handles the
  missing acceptance later (Non-Goal 2).
- Long review summary: the existing 8,000-character question bound applies; the instruction asks for a short summary.

## 5. Verification & Test Plan

- Unit, new: `modules/hub/tests/unit/features/project_management/pipeline_runs/test_requests.py` builds an SDD and a
  non-SDD request through `build_implementation_request` and asserts AC-01, AC-02 (gate obligations present; no
  `devkit`/`plan-accept`) and AC-03 (non-SDD instructions unchanged). A mention-comment test renders the SDD request
  with `build_codex_mention_comment` and asserts AC-04.
- Integration, existing: `test_agent_question_after_push_pauses_before_ci_and_uses_current_head` in
  `test_optimistic_sdd.py` stays green for AC-05; `test_enrollment_has_only_descriptive_intent_and_no_repository_readiness`
  keeps asserting that no stage or devkit text enters the instructions.
- Commands: `just test` scoped to the pipeline_runs unit and integration tests, then `just lint` and `just check`.
  No API change, so `just gen-ui-api` is not needed.
- Live (evidence only): after deployment, a Planning activity on the canary SDD repository shows the gate question,
  the applied answer commit, then Ready and merge.
