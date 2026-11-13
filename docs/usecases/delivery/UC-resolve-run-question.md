---
id: UC-resolve-run-question
title: Resolve a Run Question
summary: "An operator discovers a PR-bound question, saves clarification and explicitly applies a selected answer. Head guards and durable request identity preserve direction across stale reads and retries."
area: delivery
primary_actor: Operator
supporting_actors:
  - GitHub
  - Agent provider
status: active
capabilities:
  - CAP-PR-operator-decisions
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/api/interactions.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/control.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/outcomes.py
---

# [UC-resolve-run-question] Resolve a Run Question

## 1. Goal

- **Goal**: make an explicit clarification part of the intended PR execution,
  with a retained record of the question, chosen answer and application.
- **Scope**: ordinary Auto Hub Run questions and answer application; native SDD
  workflow approval and revocation are separate decisions.
- **Trigger**: the operator inspects a Run requiring clarification.
- **Preconditions**: the operator can access Hub and has identified the Run.
  Hub checks pending-question state, revisions, GitHub binding and current head.

## 2. Main Success Scenario

1. The operator inspects the pending question and its PR context (`CAP-PR-operator-decisions`).
   Interface: `UX-decision-inbox`, `UX-run-decisions`.

2. The operator saves the intended clarification (`CAP-PR-operator-decisions`).
   Interface: `UX-run-decisions`.

3. Hub retains the answer without continuing execution (`CAP-PR-operator-decisions`).
   Interface: `UX-run-decisions`.

4. The operator explicitly selects that saved answer to resume the Run (`CAP-PR-operator-decisions`).
   Interface: `UX-decision-inbox`, `UX-run-decisions`.

5. Hub verifies the current context and records the answer's application to one prepared attempt (`CAP-PR-operator-decisions`).
   Interface: `UX-run-decisions`.

The operator can locate the pending subject through `UX-decision-inbox` before opening its exact owner review. Optional notice-link entry follows `UC-receive-decision-notice`; authentication and exact current identity are checked before the existing owner controls enable. Native review refreshes and persists the current inspection basis before controls enable. Existing per-run entry points remain available.

## 3. Extensions

- **1a.** The operator needs to introduce a question: Hub records it against the
  current PR and blocks the Run; resumes at step 1.
   Interface: `UX-run-decisions`.

- **1b.** An agent reply has untrusted provenance or mismatched question metadata:
  Hub does not retain it as a question; this resolution flow does not start until
  a valid question is recorded.
   Off screen: provider-reply provenance is rejected before a valid Run question exists.

- **2a.** The inspected Run revision is obsolete: Hub refuses the new save without
  appending an answer; resumes at step 1 after reinspection.
   Interface: `UX-run-decisions`.

- **2b.** A save response is lost: the owner review retains its immutable request and shows Outcome unknown. Check outcome reads that request; an explicit Retry same request preserves the original payload. The confirmed saved result resumes at step 4.
   Interface: `UX-run-decisions`.

- **2c.** A recorded request ID is reused for different text: Hub refuses the
  changed input; the flow ends without replacing the earlier record.
   Interface: `UX-run-decisions`.

- **4a.** No answer is selected for a pending question: Hub refuses resume and
  retains the pending decision; resumes at step 4 after explicit selection.
   Interface: `UX-run-decisions`.

- **4b.** The PR head changed since the question: Hub refuses answer application;
  the operator inspects the changed work and this application flow ends pending
  dismissal or a fresh relevant question.
   Interface: `UX-run-decisions`.

- **4c.** The operator dismisses the pending question with a reason: Hub retains
  the dismissal and leaves execution stopped; the clarification flow ends without
  applying an answer.
   Interface: `UX-run-decisions`.

- **4d.** A completed resume request is replayed after a later pause: Hub returns
  the current paused Run without restarting it; the replay ends without a new
  application or removal of the stop.
   Interface: `UX-run-decisions`.

- **5a.** Delivery fails after answer application was committed: the prepared
  application remains recorded; later delivery reconciliation uses that attempt
  rather than applying the same receipt again.
   Interface: `UX-run-decisions`.

- **1z.** The inbox subject resolved, changed generation or failed inspection: controls remain disabled and the operator refreshes the list and explicitly reviews the current subject; resumes at step 1.
   Interface: `UX-decision-inbox`, `UX-run-decisions`.

## 4. Postconditions

- **Success guarantee**: the chosen question/answer pair is retained and bound to
  a prepared attempt through one resume receipt. This establishes preparation,
  not delivery, implementation or merge approval.
- **Minimal guarantee**: stale or changed input does not replace retained text;
  unanswered or head-stale questions cannot silently resume execution. Dismissal
  and old receipt replay do not restart a stopped Run.

## 5. Acceptance Criteria (Given / When / Then)

Rules used from `CAP-PR-operator-decisions`: blocked questions and provenance
(1, 5–7), revision/request identity (2–4), save versus application (8–11), delivery
recovery and later-stop preservation (12–13), and dismissal (14).

### DEC-01: Apply a saved answer once

- **Covers**: main success scenario.
- **Given**: a pending question against the unchanged head of an ordinary Run.
- **When**: the operator saves an answer and explicitly resumes using it.
- **Then**: saving leaves the Run blocked, while resume prepares one attempt containing the question and selected answer and marks that answer applied.

### DEC-02: Record an operator-introduced clarification

- **Covers**: 1a.
- **Given**: an eligible ordinary Run without a pending question.
- **When**: the operator asks against its inspected revision.
- **Then**: the question records the current PR head and the Run becomes blocked.

### DEC-03: Ignore a forged or stale question signal

- **Covers**: 1b.
- **Given**: an implementation reply from another author or carrying another attempt/head.
- **When**: Hub observes it.
- **Then**: no question is retained from that reply and it does not block the Run as a question.

### DEC-04: Reject a stale answer save

- **Covers**: 2a.
- **Given**: the Run revision changed after inspection.
- **When**: an answer is submitted under the obsolete revision.
- **Then**: Hub returns a conflict and the question has no newly appended answer.

### DEC-05: Recover a lost answer-save response

- **Covers**: 2b.
- **Given**: an answer was saved but its response was lost.
- **When**: its identical request ID/text is replayed, including with a refreshed inspected revision.
- **Then**: Hub returns the same answer ID and retains one answer record for that request.

### DEC-06: Refuse replacement under a recorded identity

- **Covers**: 2c.
- **Given**: a question or answer request ID already identifies retained text.
- **When**: different text is submitted with that ID.
- **Then**: Hub returns a conflict and the original text remains unchanged.

### DEC-07: Require explicit answer selection

- **Covers**: 4a.
- **Given**: an open or answered pending question.
- **When**: ordinary resume omits the selected saved answer.
- **Then**: Hub refuses resume and retains the question as pending.

### DEC-08: Refuse application after head movement

- **Covers**: 4b.
- **Given**: a saved answer to a question at an earlier PR head.
- **When**: the operator tries applying it after another push.
- **Then**: Hub returns a conflict without marking the answer applied.

### DEC-09: Dismiss without continuing execution

- **Covers**: 4c.
- **Given**: a pending question that the operator has inspected and considers obsolete.
- **When**: the operator dismisses it with the current revision and a reason.
- **Then**: the question becomes dismissed and the Run remains stopped.

### DEC-10: Preserve a stop newer than a resume receipt

- **Covers**: 4d.
- **Given**: a successful resume receipt followed by a later operator pause.
- **When**: the original resume request is replayed.
- **Then**: Hub returns the current paused revision without creating another attempt.

### DEC-11: Keep applied direction through delivery failure

- **Covers**: 5a.
- **Given**: a committed answer application whose subsequent delivery times out.
- **When**: the resume receipt is replayed and delivery is reconciled.
- **Then**: the same applied answer remains in the prepared request and no duplicate application/attempt is created by that replay.

## 6. Evidence boundary

The examples derive from the production source and named tests in
`CAP-PR-operator-decisions`, particularly `test_interactions.py` and
`test_questions.py`. They were inspected rather than executed for this document.
They do not establish a live provider result, deployment or a verified SDD
baseline for Auto Hub.

### INBOX-01: Preserve exact owner review

- **Given** an observed pending decision in the shared inbox,
- **When** the operator selects Review,
- **Then** the exact owner subject loads and native controls wait for persisted inspection; an obsolete selection stays disabled until explicit reinspection.
- **Covers**: 1z and the discovery entry.


### CONTINUE-01: Retain explicit outcome and original retry

- **Covers**: 2b, 4d, 5a.
- **Given** a saved answer or prepared application whose response or refresh failed,
- **When** the operator checks its original outcome or explicitly retries that request,
- **Then** the original identity/payload stays bound, a missing record remains unknown, saved text/application remain separate from delivery and a later pause remains current.
