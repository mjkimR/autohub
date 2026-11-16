---
id: UC-complete-sdd-workflow
aliases: [UC-decide-sdd-proposal, UC-preview-sdd-milestone, UC-execute-sdd-batch]
title: Follow repository-owned SDD work through PR delivery
summary: "An operator follows an SDD activity as ordinary PR work, answers agent questions and explicitly resumes it, then observes repository-owned GitHub CI and policy-controlled merging."
area: sdd
primary_actor: Project operator
supporting_actors: [Repository agent, GitHub, Repository CI]
status: active
capabilities: [CAP-SDD-native-delivery, CAP-PR-pull-request-delivery, CAP-PR-operator-decisions]
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
  - modules/hub-ui/src/lib/features/project-management/repositories/SddUnitActions.svelte
---

# [UC-complete-sdd-workflow] Follow repository-owned SDD work through PR delivery

## 1. Goal

- **Goal**: Deliver the requested repository work while keeping questions and
  merge authorization explicit.
- **Scope**: ordinary PR progression after activity registration.
- **Trigger**: the operator opens the activity Run.
- **Preconditions**: the operator is authenticated and knows the Run identity.

## 2. Main Success Scenario

1. The operator opens the selected unit's execution history or deliberately enrolls an existing PR with an explicitly entered PR number and its descriptive activity context
   (`CAP-SDD-native-delivery`). Interface: `UX-sdd-execution`, `UX-run-page`, `UX-sdd-run`.
2. Hub dispatches the request through the ordinary implementation owner
   (`CAP-PR-pull-request-delivery`). Interface: `UX-run-page`.
3. The agent follows repository instructions and publishes work or a question
   (`CAP-PR-pull-request-delivery`). Interface: `UX-run-page`.
4. The operator saves an answer if the agent needs input
   (`CAP-PR-operator-decisions`). Interface: `UX-run-decisions`, `UX-decision-inbox`.
5. The operator explicitly resumes with the selected saved answer
   (`CAP-PR-operator-decisions`). Interface: `UX-run-decisions`, `UX-decision-inbox`.
6. The operator marks the PR ready when it may merge
   (`CAP-PR-pull-request-delivery`). Off screen: the operator changes Draft status in GitHub.
7. Hub observes current-head GitHub checks and the policy-controlled merge outcome
   (`CAP-PR-pull-request-delivery`). Interface: `UX-run-page`, `UX-pipeline-runs`.

## 3. Extensions

- **3a.** A correlated question is observed before or after a push: Hub pauses
  progression for input; resumes at step 4. Interface: `UX-run-decisions`, `UX-decision-inbox`.
- **4a.** The operator saves no answer or leaves it unapplied: work stays waiting;
  the use case ends without implicit resume. Interface: `UX-run-decisions`, `UX-decision-inbox`.
- **5a.** The question/head/revision changed: Hub refuses the stale resume; the
  operator inspects the current question and resumes at step 4.
  Interface: `UX-run-decisions`, `UX-decision-inbox`.
- **6a.** The PR remains or returns to Draft: merging remains unavailable; resumes
  at step 6. Interface: `UX-run-page`.
- **7a.** CI fails, the head moves or project merge policy withholds merge: the
  ordinary PR owner repairs or waits under its existing limits; resumes at step 7
  or ends at an explicit blocked/failed outcome. Interface: `UX-run-page`.
## 4. Postconditions

- **Success guarantee**: the Run records its actual PR delivery outcome.
- **Minimal guarantee**: an answer is not merge authority; Hub never claims to
  have proved the repository's internal SDD workflow or correctness.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDD-native-delivery` descriptive activity context;
`CAP-PR-operator-decisions` durable input and explicit resume;
`CAP-PR-pull-request-delivery` Draft/current-head CI/merge policy.

### SDD-FOLLOW-01: Observe ordinary delivery

- **Covers**: main success scenario.
- **Given** an optimistic SDD activity with repository-owned checks.
- **When** its agent publishes work and the operator marks the PR ready.
- **Then** ordinary current-head CI and project merge policy determine the PR outcome.

### SDD-FOLLOW-02: Keep input explicit

- **Covers**: 3a, 4a, 5a.
- **Given** an agent question around a push.
- **When** the question is saved/answered or a stale resume is attempted.
- **Then** input remains bound to its current question/head; saved text alone neither resumes nor authorizes merge.

### SDD-FOLLOW-03: Withhold merge

- **Covers**: 6a, 7a.
- **Given** Draft status, changed head, failing CI or disabled auto-merge.
- **When** Hub advances the Run.
- **Then** it follows the ordinary PR refusal/wait contract without repository workflow reevaluation.

### SDD-FOLLOW-04: Continue after explicit resume

- **Covers**: main success scenario, step 5.
- **Given** a saved answer for the current Run question and revision.
- **When** the operator explicitly resumes.
- **Then** Hub attempts the committed continuation promptly; replay creates no further prompt attempt and deferred delivery remains recoverable.
