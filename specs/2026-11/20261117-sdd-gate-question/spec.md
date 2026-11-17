---
id: SPEC-sdd-gate-question
title: Surface repository workflow gates through the question channel
summary: SDD activity instructions ask the repository agent to raise a stopped human workflow gate as an attempt-bound question so the operator's explicit answer, resume and Ready status keep acceptance before merge.
status: in-progress
created: 2026-11-17
related_capabilities: [CAP-SDD-native-delivery, CAP-PR-operator-decisions]
related_usecases: [UC-complete-sdd-workflow]
workflow: sdd-spec-feature
---

# [SPEC-sdd-gate-question] Surface repository workflow gates through the question channel

## 1. Problem Statement & Motivation

A repository-owned SDD activity can finish its work and then stop at a human approval gate of the repository's
own workflow, such as devkit's `plan-accept` after Planning. The current SDD activity instructions ask the agent to
use the question channel only for "missing direction", and the shared mention template says to ask "before pushing".
In the observed Planning activity on a canary repository, the agent pushed its Planning result, set the proposal to
review and stopped at `plan-accept` without a question marker. Hub therefore showed only the generic Draft wait.

The operator could not tell that the agent had finished and was asking for a decision, had no channel to accept,
request changes or reject, and could only mark the PR Ready. Merging then lands a proposal still in review without
the repository's acceptance record, and the next Development activity is refused by the repository workflow.

The question channel already accepts an SDD question after a push, binds it to the current head and resumes only
with an explicit saved answer (`CAP-PR-operator-decisions`, `UC-complete-sdd-workflow` extension 3a). What is
missing is the instruction that a stopped human gate is such a question, and the documented order in which the
operator's answer is applied before Ready status and merge.

## 2. User Stories

- **US-1**: As a project operator, I want an SDD activity that stops at a repository approval gate to appear as an
  open question with the agent's review summary, so that I know the work awaits my decision rather than more work.
- **US-2**: As a project operator, I want my saved answer (accept, request changes or reject) to reach the
  repository agent through an explicit resume, so that the repository records the decision before I mark the PR
  Ready.
- **US-3**: As a repository agent, I want the activity instructions to say how to raise a gate after pushing
  completed work and how to apply the relayed answer, so that I do not infer approval or stop silently.

`UC-complete-sdd-workflow` changes: its question extension gains the gate case and the answer-before-Ready order.

## 3. Non-Goals

1. **Scope Excluded**: a typed gate marker, gate-specific answer buttons or an approval card in Hub. The gate uses
   the existing free-text question and answer.
   **When to Reconsider**: live use shows free-text answers are misapplied by repository agents; that change must
   revisit `ADR-remove-native-sdd-compatibility`.
2. **Scope Excluded**: Hub reading, evaluating or enforcing repository workflow state (proposal status, gate
   records, `devkit workflow next`). Hub does not refuse Ready status or merge because a gate was not answered;
   `ADR-repository-owned-sdd-execution` keeps workflow interpretation with the repository agent.
3. **Scope Excluded**: changes to the generic (non-SDD) mention template, question parsing, answer storage, resume
   or merge policy.
4. **Scope Excluded**: naming devkit commands or gate IDs in Hub instructions; the instruction stays generic over
   any repository workflow.
5. **Scope Excluded**: repairing the already-open canary Planning PR; its operator applies the acceptance manually.

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] SDD activity instructions name the gate question
- **Given** a Run with an SDD activity snapshot of either activity kind
- **When** Hub builds its implementation request
- **Then** the request instructions state that a stop at a human approval or decision gate of the repository
  workflow MUST be raised through the question marker, after pushing completed work, with a summary the operator
  can decide from and the expected answer forms (accept, request changes, reject)
- **And** they state that the agent MUST NOT record or infer the operator's decision before an answer arrives

### [AC-02] Instructions describe applying the relayed answer
- **Given** the same SDD activity request
- **When** Hub builds its instructions
- **Then** they state that a resumed attempt carrying the operator's answer applies it as the operator's decision
  under the repository's own workflow, pushes the result and leaves the PR Draft
- **And** they contain no devkit command, gate ID or workflow stage name (`devkit`, `plan-accept`)

### [AC-03] Non-SDD requests are unchanged
- **Given** a Run without an SDD activity snapshot
- **When** Hub builds its implementation request
- **Then** the instructions contain no gate-question text and equal the current non-SDD instructions

### [AC-04] The mention comment carries the gate instruction without a conflicting push rule
- **Given** an SDD activity implementation request
- **When** Hub renders its Codex mention comment
- **Then** the comment contains the gate instruction from AC-01 and the question marker block
- **And** the SDD instruction states that, in this activity, a question raised after pushing completed work remains
  valid, so the generic "stop before pushing" sentence does not forbid the gate case

### [AC-05] A gate question after a push follows the existing decision flow
- **Given** an optimistic SDD Run whose agent pushed a new head and replied with a correlated question marker
  bound to the dispatched head
- **When** Hub advances the Run, the operator saves an answer and explicitly resumes
- **Then** the Run is `blocked` with one open question bound to the pushed head, the PR stays Draft until the
  operator changes it, and the resume returns `200` with state `implementing`
- **And** the saved answer alone neither resumes the Run nor authorizes merge

## 5. Verification Boundary

AC-01 to AC-04 are request/template unit tests; AC-05 is covered by the existing optimistic SDD integration test
and stays a regression check. Whether a live repository agent follows the instruction is observed separately on the
deployed Hub with a Planning activity on the canary SDD repository: question raised after push, answer applied as a
repository acceptance commit, then Ready and merge. That observation is evidence, not an acceptance criterion.

## 6. Assumptions

- The repository agent can push completed work and still end its reply with the question marker; the marker's
  `head` remains the dispatched head, which the parser already requires.
- An operator's saved answer relayed through Hub is the operator's decision for the repository workflow; Hub makes
  no claim about how the repository records it.
