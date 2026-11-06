---
id: CAP-PR-operator-decisions
title: Run Questions and Operator Decisions
summary: "Retain PR-bound questions and append-only answers, discover pending decisions across projects, and apply an explicitly selected answer through revision-checked resume. Discovery preserves owner authority and request replay identity."
area: delivery
status: active
usecases:
  - UC-resolve-run-question
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/api/interactions.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/interactions.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/control.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/outcomes.py
---

# [CAP-PR-operator-decisions] Run Questions and Operator Decisions

## 1. Summary

A question records a decision needed for a particular PR head and execution
attempt. Saving an answer retains the operator's direction; applying it is a
separate resume operation that prepares execution with that direction.
`UC-resolve-run-question` describes this ordinary PR clarification flow.

## 2. Scope & Boundary

- **In-Scope**: operator questions, trusted agent question ingestion, stored
  answers, explicit dismissal, ordinary-run answer application and resume replay.
- **Out-of-Scope**: `CAP-PR-pull-request-delivery` owns dispatch, pause/cancel,
  CI and merge; `CAP-SDD-workflow-control` owns native workflow questions,
  approval/revision/revocation and native resume semantics; `CAP-MCP-tool-access`
  owns MCP access to the shared operations.
- **Scope Excluded**: editing recorded question/answer text, automatic answer
  application, treating comments as approval and cancellation of already-sent
  provider work. A saved/applied clarification is not PR merge approval.

The question/answer HTTP handlers and record tables are shared with native SDD
Runs. `PipelineRunControl.resume_run` delegates a Run with an SDD snapshot to
`SddControl`; the ordinary resume guarantees below do not replace that branch.
An ordinary Run rejects native `decision` or `workflow_answer` input rather than
interpreting it as ordinary clarification. Native revocation is not an ordinary
question-state transition.

## 3. Business Rules & Policies

1. **Blocked decision**: WHEN Hub accepts a question, Hub MUST retain it against the PR head and block Run progression pending explicit resolution. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_answer_is_saved_without_execution_then_applied_once` and `test_agent_question_is_attempt_bound_and_delivery_failure_preserves_answer`.
2. **Revision guard**: IF a new answer uses an obsolete Run revision, THEN Hub MUST reject it with HTTP 409 without appending that answer. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_stale_answers_and_missing_resume_contract_do_not_mutate`.
3. **Question identity**: WHEN a question request is identically replayed, Hub MUST return the original question instead of creating a second record. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_question_request_replay_and_answer_id_conflict`.
4. **Immutable request content**: IF an existing question or answer request ID is reused with changed text, THEN Hub MUST return HTTP 409 instead of replacing the recorded text. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_question_request_replay_and_answer_id_conflict`.
5. **Trusted agent provenance**: WHEN ingesting a reply as a question, Hub MUST require the trusted Codex connector author and the current attempt's bound marker before blocking on it. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_agent_question_is_attempt_bound_and_delivery_failure_preserves_answer`.
6. **Exact marker binding**: IF the question marker's attempt or head differs from the expected delivery context, THEN the parser MUST ignore it as a question signal. Check: [`test_questions.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_questions.py), `test_question_requires_exact_attempt_and_head`.
7. **Bounded question text**: IF an agent question is empty, exceeds 8,000 characters, includes a prohibited agent mention/hidden marker or is not a string, THEN the parser MUST ignore it as a question signal. Check: [`test_questions.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_questions.py), `test_invalid_question_is_not_an_execution_signal` and `test_json_escaping_does_not_reduce_the_question_length_limit`.
8. **Save without execution**: WHEN an answer is saved or identically replayed, Hub MUST create no execution attempt for that save. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_answer_is_saved_without_execution_then_applied_once`.
9. **Explicit answer selection**: WHILE a question is `open` or `answered`, IF ordinary resume does not select a saved answer, THEN Hub MUST return HTTP 409 instead of resuming. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_pending_question_and_changed_head_require_explicit_resolution`.
10. **Head-specific application**: IF the current PR head differs from the pending question's head, THEN ordinary resume MUST reject application of its saved answer with HTTP 409. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_pending_question_and_changed_head_require_explicit_resolution`.
11. **One prepared application**: WHEN a selected answer is validly applied, Hub MUST bind it to one newly prepared attempt containing the question and selected answer under the resume receipt. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_answer_is_saved_without_execution_then_applied_once` and `test_concurrent_answer_and_resume_are_single_requests`.
12. **Delivery failure preserves application**: IF delivery fails after an answer has been applied to an attempt, THEN Hub MUST retain that applied answer/attempt for delivery recovery rather than apply it to another attempt on receipt replay. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_agent_question_is_attempt_bound_and_delivery_failure_preserves_answer`.
13. **Replay cannot unpause**: WHEN a successful resume request is replayed after a later pause, Hub MUST return the current paused Run without undoing that stop or creating another attempt. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_old_resume_replay_does_not_unpause_a_later_stop`.
14. **Dismissal is not resume**: WHEN a pending question is dismissed with the current revision and a reason, Hub MUST close the question while leaving the Run stopped for inspection. Check: [`test_interactions.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_interactions.py), `test_pending_question_and_changed_head_require_explicit_resolution`.
15. **Bounded marker search**: WHEN looking for an agent question marker, the parser MUST restrict its search to the first 112,000 reply characters. Source: [`questions.py`](../../../modules/hub/app/features/project_management/pipeline_runs/questions.py), `_MAX_REPLY_CHARS`; bounded-scan example: [`test_questions.py`](../../../modules/hub/tests/unit/features/project_management/pipeline_runs/test_questions.py), `test_question_scan_remains_bounded`.

### Pending discovery

WHEN an authenticated operator lists decisions, Hub MUST expose visible nonterminal Run questions in open or answered state through a persisted discovery projection. Saving retains Answer saved; application or dismissal removes the row in the owner transaction. Check: `test_discovery_question_lifecycle_and_exact_owner` and `test_projection_rolls_back_with_owner` in [test_discovery.py](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_discovery.py).

WHEN listing a changing worklist, Hub MUST use oldest waiting time and stable key with a limit-plus-one keyset query and zero provider calls. Ordinary waiting time is question creation time. Check: `test_keyset_bounded_and_cursor_filters` in the same test file.

The authenticated `GET /api/v1/pipeline-runs/decisions` accepts optional `project_id`, `kind`, `question_state` (open/answered), `cursor` and `limit` (default 20, range 1–100). It returns `items`, `has_more` and `next_cursor`; malformed or filter-mismatched cursors return 422, unknown projects 404. It follows existing run-read visibility: admitted users share projects; no independent project ACL is introduced. Refresh restarts pagination because new generations may precede a retained cursor.

`POST /api/v1/pipeline-runs/decisions/review` accepts an exact `key` and `fingerprint`. Missing/ended owners return 404; changed generations return 409. The Run question read `GET /api/v1/pipeline-runs/{run_id}/questions/{question_id}` resolves that exact owner question, including one outside the first history page. `UX-decision-inbox` opens `UX-run-decisions`; filters and loaded cursor page persist when it closes.

### Exact owner outcomes and continuation

WHEN an authenticated operator queries one request outcome, Hub MUST read the exact selected owner namespace within that Run and one database transaction, without provider/repository calls or mutation. Missing retained requests remain `record_state: unknown`; missing Runs return 404. Check: `test_exact_outcomes_namespace_unknown_and_no_external_reads` in [test_outcomes.py](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_outcomes.py).

WHEN an application receipt exists, Hub MUST disclose its retained attempt and delivery facts separately from current Run state and authority. A later stop remains current. No attempt or delivery completion is inferred from a prepared receipt. Check: `test_application_outcome_survives_later_pause_and_receipt_replay` in the same file.

WHILE a submission outcome is uncertain, the owner review MUST retain its original request ID and complete payload in memory across refresh and temporary close. Explicit retry replays that payload; replacement submissions remain disabled. A browser reload cannot restore unacknowledged intent. Structured request-validation rejection permits correction after current review; ambiguous owner errors, including publication runner timeout422, remain unknown. Check: [decision-intents.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/decision-intents.integration.test.ts).

WHEN a mutation is acknowledged and a subsequent read fails, the interface MUST retain the recorded identity and saved text with a refresh error. Saving never selects an answer for application. Historical outcome selection has its own displayed request identity and read action. Check: [RunDecisionsDialog.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.integration.test.ts).

## 4. Interfaces & Data Contracts

### HTTP surface

Base: `/api/v1/pipeline-runs/{run_id}`. The application supplies the authenticated
actor; requests do not supply authoritative actor identity.

| Method and suffix | Input/result |
| --- | --- |
| `GET /decision-outcomes/{request_id}` | Required `operation` selecting question, answer or resume; `DecisionOutcome` with current Run revision/state, observed time and nullable owner evidence. Invalid discriminator/UUID returns 422. |
| `GET /questions` | `offset >= 0`, `limit` 1–100; `items`, `total_count`, current `run_revision` |
| `POST /questions` | `request_id`, `expected_revision`, `question`; returns `QuestionRead` |
| `POST /questions/{question_id}/answers` | `request_id`, `expected_revision`, `answer`; returns `AnswerRead` |
| `POST /questions/{question_id}/dismiss` | `expected_revision`, reason of 1–2,000 characters; returns the dismissed question |
| `POST /resume` | `request_id`, `expected_revision`, selected `answer_id` for a pending ordinary question; returns current `PipelineRunRead` |

Question and answer text is stripped and constrained to 1–8,000 characters;
schemas reject unknown fields, agent mentions matched by `CODEX_MENTION` and
`<!--` hidden-marker prefixes. Question creation checks the captured GitHub
binding, current project revision, open PR and branch before saving the head.
Missing Runs return 404. State/identity/revision conflicts return 409. Invalid
payloads return 422. A failed or timed-out PR read during question creation
returns 502 or 504 respectively. No new stable error code is defined here.

The outcome response includes question/answer identity and saved text, applied attempt, execution state, delivery state/time, native channel, publication state/candidate heads, matched envelope, inspected head/digest and current authority/hold. Missing facts are null with `unavailable_reason`. Multiple prepared candidates are listed without choosing one as authoritative. No request digest, credential or generic completion flag is returned. Retained results remain readable after the Run ends; existing retention still applies.

### Records and transitions

- `RunQuestion`: request ID, Run/optional attempt ID, `head_sha`, question,
  actor/source, state and optional resolution. `open` and `answered` both count
  as pending; the service accepts at most one pending question per Run.
- `RunAnswer`: request ID, question ID, answer, actor and nullable
  `applied_attempt_id`. Distinct saved answers remain separate records. New saves
  increment Run revision and set the pending question to `answered`.
- Ordinary answer application: checks the Run and project before/after the PR
  read, appends the question/selected answer to the attempt's immutable request,
  marks the question `applied`, sets `applied_attempt_id` and records a
  `RunResumeReceipt` in the same transaction that prepares dispatch.
- Dismissal: records `dismissed` and actor/reason; increments Run revision and
  leaves the Run stopped. It neither applies a saved answer nor creates a resume
  receipt. A separate inspected resume can continue after dismissal.

The question/answer request ID is also its record ID. Replay identity includes
Run/question ownership, text and authenticated actor, but permits a refreshed
`expected_revision` for the same saved record. Ordinary resume identity instead
digests the Run, actor and full request, including the inspected revision and
chosen answer. Changing its payload under the same receipt ID conflicts.
Receipt replay returns current Run state, not the original response snapshot.

`check_revision` refuses new decision mutations on ended Runs; identical
question/answer replays are looked up before that check and do not mutate them.
Ordinary resume requires `paused` or `blocked`, a valid current GitHub binding and
an unapplied answer belonging to the current pending question. Preparing an
answer for execution does not prove that the provider received or implemented it.

The prepared request instructs the agent to apply the clarification within the
original scope and ask again if acceptance criteria change. CI/conflict repairs
derive from the prior request snapshot and retain those clarified instructions;
this propagation is source-inspected in `PipelineRunControl.resume_run` and
`CIProgress.apply`, rather than separately established by the initial-answer and
delivery-recovery examples above.

The schema links questions and resume receipts to their Run with `ON DELETE
CASCADE`, and answers to their question with the same cascade. Their history
therefore follows Run retention and is not an independent permanent archive.
The Work Item protection conditions in `CAP-WORK-work-plan-execution` still
govern whether its linked Run can be pruned.

### Agent question signal

The recognized signal is a single-line HTML comment with an `autohub-question`
JSON object containing `attempt`, `head` and `question`. The adapter normalizes the
connector's `[bot]` suffix and ignores replies older than the delivery. The
parser scans the first 112,000 characters (`12 * 8,000 + 16,000`) and requires the
delivery's exact attempt/head. The expansion allowance supports escaped JSON
Unicode without reducing the decoded 8,000-character question limit. Accepted
reply IDs produce a deterministic question UUID using `uuid5(NAMESPACE_URL,
f"autohub-question:{run.id}:{reply.external_id}")`; this identity is source-defined
in `ImplementationProgress.apply`.
In ordinary implementation observation, an already-moved PR head progresses to
CI before question parsing; a stale reply cannot re-block that delivered attempt.
The run decision instructions (`CAP-PR-operator-decisions`)
retain the wire example and operator/client procedure.

## 5. Source and verification evidence

Inspected source: [`api/interactions.py`](../../../modules/hub/app/features/project_management/pipeline_runs/api/interactions.py),
[`usecases/interactions.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/interactions.py),
[`interaction_service.py`](../../../modules/hub/app/features/project_management/pipeline_runs/interaction_service.py),
[`interaction_repo.py`](../../../modules/hub/app/features/project_management/pipeline_runs/interaction_repo.py),
[`interaction_schemas.py`](../../../modules/hub/app/features/project_management/pipeline_runs/interaction_schemas.py),
[`questions.py`](../../../modules/hub/app/features/project_management/pipeline_runs/questions.py),
[`usecases/control.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/control.py),
[`usecases/ci.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/ci.py),
[`models.py`](../../../modules/hub/app/features/project_management/pipeline_runs/models.py),
[`usecases/implementation.py`](../../../modules/hub/app/features/project_management/pipeline_runs/usecases/implementation.py)
and [`adapters/codex_github_mention.py`](../../../modules/hub/app/features/project_management/pipeline_runs/adapters/codex_github_mention.py).

The named unit/integration tests were inspected, not executed while authoring.
The concurrent-answer/resume test requires PostgreSQL and skips on SQLite.
Integration examples use controlled GitHub responses and do not prove live
provider behavior, deployment or Auto Hub's own SDD baseline. Native decision
revocation remains outside this ordinary-run contract.
