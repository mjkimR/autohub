---
id: UC-start-sdd-activity
title: Start a proposal Planning or Development activity
summary: "A project operator starts an eligible proposal activity and obtains its tracked PR run, reusing an owned activity PR after a lost response. The goal ends at registration rather than completion of the agent's work."
area: sdd
primary_actor: Project operator
supporting_actors:
  - GitHub
  - devkit runtime
status: active
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-runtime-isolation
entrypoints:
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/api.py
---

# [UC-start-sdd-activity] Start a proposal Planning or Development activity

## 1. Goal

- **Goal**: Register the correct proposal activity as one tracked PR execution so
  the operator can follow its work and decisions without manually creating its branch.
- **Scope**: Auto Hub native SDD activity start.
- **Trigger**: The operator requests Planning or Development for a proposal.
- **Preconditions**: The operator is authenticated to Auto Hub.

## 2. Main Success Scenario

1. The operator selects the proposal, activity, base and execution preferences
   (`CAP-SDD-native-delivery`, rules 3–7).
   Interface: `UX-sdd-proposals`.

2. Hub checks the project, base policy and proposal eligibility; for Planning and
   Development it evaluates the base with the runtime the base's lock pins
   (`CAP-SDD-native-delivery`, rules 1–3, 18; `CAP-SDD-runtime-isolation`, rules 1–6, 15).
   Interface: `UX-sdd-proposals`.

3. Hub creates the activity's branch and PR without resolving a runtime
   (`CAP-SDD-native-delivery`, rules 4–5; `CAP-SDD-runtime-isolation`, rule 14).
   Interface: `UX-sdd-proposals`.

4. Hub enrolls the PR with its proposal binding and effective activity effort,
   evaluating its head with that head's locked runtime
   (`CAP-SDD-native-delivery`, rules 4–7; `CAP-SDD-runtime-isolation`, rules 1–6).
   Interface: `UX-sdd-proposals`.

5. Hub returns the tracked run for the operator to follow
   (`CAP-SDD-native-delivery`, rules 4–5).
   Interface: `UX-sdd-proposals`.

## 3. Extensions

- **2a.** Project is not enabled/configured for native SDD: Hub refuses with HTTP
  422 / `INVALID_REQUEST`; no activity is created and the use case ends.
   Interface: `UX-sdd-proposals`.

- **2b.** Proposal or base is absent: Hub refuses with HTTP 422 / `INVALID_REQUEST`;
  no activity branch is created and the use case ends.
   Interface: `UX-sdd-proposals`.

- **2d.** Proposal lifecycle, size or intent is ineligible: Hub refuses with HTTP
  409 / `CONFLICT`; no activity branch is created and the use case ends.
   Interface: `UX-sdd-proposals`.

- **2c.** Base uses adaptive development: Hub refuses with
  `SDD_LIFECYCLE_INACTIVE`; no activity branch or PR is created and the use case ends.
   Interface: `UX-sdd-proposals`.

- **2e.** The base cannot supply a runtime: Hub refuses with the runtime
  code (`SDD_RUNTIME_UNLOCKED`, `SDD_RUNTIME_SOURCE_UNSUPPORTED`,
  `SDD_RUNTIME_PYTHON_UNSUPPORTED`, `SDD_BUNDLES_MISSING`, or a recorded
  `SDD_RUNTIME_SOURCE_UNAVAILABLE` or `SDD_RUNTIME_INSTALL_FAILED`) before any
  branch is created; the use case ends until the repository or connector is fixed.
   Interface: `UX-sdd-proposals`.

- **2f.** The base runtime is still being installed: Hub refuses with HTTP
  503 / `SDD_RUNTIME_PREPARING` before any branch is created. Replaying the same
  request returns that recorded refusal; the operator starts the activity again
  after the install and the use case resumes at step 1.
   Interface: `UX-sdd-proposals`.

- **3a.** Existing branch is unrelated: Hub refuses with HTTP 409 / `SDD_BRANCH_EXISTS`;
  the existing branch is unchanged and the use case ends.
   Interface: `UX-sdd-proposals`.

- **3b.** Existing branch has Hub's own open activity PR: Hub reuses the PR instead
  of creating another branch or PR; resumes at step 4.
   Interface: `UX-sdd-proposals`.

- **3c.** Runner/Git execution cannot finish: Hub reports HTTP 422 /
  `INVALID_REQUEST`; the operator inspects remote artifacts before retrying and
  the use case ends without a claim of rollback.
   Interface: `UX-sdd-proposals`.

- **4a.** Enrollment fails after PR creation: The start does not return a successful
  tracked run; the operator can retry the owned activity PR path after correcting
  the reported enrollment error; the use case ends with remote artifacts retained.
   Interface: `UX-sdd-proposals`.

- **4b.** The head's runtime becomes unavailable between the base check and
  enrollment (for example evicted): enrollment fails with HTTP 503 /
  `SDD_RUNTIME_PREPARING` after the PR exists; as in 4a the PR is retained, and
  retrying the owned activity PR path after the install resumes at step 4.
   Interface: `UX-sdd-proposals`.

Milestone observations in `UC-preview-sdd-milestone` supply no start authority. Step 2 evaluates native admission afresh; preview scheduling introduces no additional start gate.

## 4. Postconditions

- **Success guarantee**: The returned run binds the intended proposal and activity
  PR. Planning uses its review branch; Development is enrolled for handoff-first work.
- **Minimal guarantee**: Pre-start admission refusals create no activity branch or
  PR. A failure after remote writes does not imply their rollback or completion of
  the activity; an unrelated branch is never overwritten for recovery.

## 5. Acceptance Criteria (Given / When / Then)

Applicable rules: `CAP-SDD-native-delivery` rules 1–7 and 18 define admission, activity
artifacts, ownership recovery and effort selection. Rule 17 defines the later
Development handoff; it is not a prerequisite for successful registration.
`CAP-SDD-runtime-isolation` rules 1–6, 14 and 15 own runtime selection,
preparation and bundle refusals; the capability owns all evaluation and runtime
admission guarantees.

### SDD-START-01: Register eligible Planning

- **Covers**: main success scenario.
- **Given**: An enabled SDD project and a draft proposal with allowed size and
  eligibility satisfied on the selected base.
- **When**: The operator starts Planning with an effort override.
- **Then**: A ready activity PR and bound run are returned, the branch's proposal
  is reviewing and the explicit effort is retained.

### SDD-START-02: Register eligible Development

- **Covers**: main success scenario.
- **Given**: An accepted proposal on the base with an activity effort hint.
- **When**: The operator starts Development without an override.
- **Then**: A draft Development PR is enrolled for handoff-first execution with
  the hint's effort; the response does not claim agent completion.

### SDD-START-03: Refuse missing project setup

- **Covers**: 2a.
- **Given**: A project without native SDD mode or an enabled GitHub binding.
- **When**: The operator starts an activity.
- **Then**: The request is invalid and no activity branch or PR is created.

### SDD-START-04: Refuse a missing proposal or base

- **Covers**: 2b.
- **Given**: The proposal anchor or selected base does not exist.
- **When**: The operator requests that activity.
- **Then**: An invalid request is returned before an activity branch is created.

### SDD-START-10: Refuse an ineligible proposal

- **Covers**: 2d.
- **Given**: An XL draft, an unresolved decomposition/intent gate or a nonaccepted
  Development proposal.
- **When**: The operator requests that activity.
- **Then**: A conflict explains the unmet condition before an activity branch is created.

### SDD-START-05: Respect inactive lifecycle

- **Covers**: 2c.
- **Given**: The evaluated base approach is adaptive development.
- **When**: The operator requests Planning or Development.
- **Then**: `SDD_LIFECYCLE_INACTIVE` is returned without a new branch or PR.

### SDD-START-06: Protect an unrelated branch

- **Covers**: 3a.
- **Given**: The expected activity branch exists without Hub's ownership marker.
- **When**: The operator starts the activity.
- **Then**: A conflict is returned and the branch is not changed.

### SDD-START-07: Recover the owned PR

- **Covers**: 3b.
- **Given**: The activity branch already carries Hub's marker-bearing open PR.
- **When**: The operator retries the start.
- **Then**: Hub enrolls that PR without another branch or PR creation.

### SDD-START-08: Report an unavailable runner

- **Covers**: 3c.
- **Given**: Git or the isolated runner cannot finish branch creation.
- **When**: The operator starts the activity.
- **Then**: Hub reports the runner failure and does not claim remote rollback.

### SDD-START-09: Retain a PR when enrollment fails

- **Covers**: 4a.
- **Given**: Hub created the activity PR and enrollment then fails.
- **When**: The start returns the enrollment error.
- **Then**: The PR remains discoverable for owned-PR recovery and no successful
  tracked run is reported by that failed request.

### SDD-START-11: Refuse Planning from a base without a devkit lock

- **Covers**: 2e.
- **Given**: The selected base has no root `uv.lock` declaring `devkit-spec`.
- **When**: The operator starts Planning or Development.
- **Then**: `SDD_RUNTIME_UNLOCKED` is returned and no activity branch or PR is created.

### SDD-START-12: Report a runtime still being prepared

- **Covers**: 2f.
- **Given**: No cached runtime exists for the base's lock identity.
- **When**: The operator starts Planning or Development.
- **Then**: HTTP 503 `SDD_RUNTIME_PREPARING` is returned with one install started
  and no activity branch or PR exists.

## 6. Source and Verification Boundary

The activity source and inspected tests are linked in `CAP-SDD-native-delivery`.
The runner-failure, post-PR enrollment-failure and runtime-refusal outcomes
(2e, 2f, 4b) follow source control flow; the cited activity tests do not establish
dedicated coverage for those failure paths through activity start. The runtime
refusals themselves are covered by the `CAP-SDD-runtime-isolation` checks. Live provider execution is outside this registration goal.

## 7. Shared batch exclusion and recovery

The individual registration path shares durable activity reservations with `UC-execute-sdd-batch`. A winning batch claim or individual claim preserves the exact owner rather than creating competing artifacts. Enrollment failure or response loss retains the original candidate/PR/request evidence; recovery checks those saved artifacts. Missing or retired evidence never means permission to start again. See `CAP-SDD-native-delivery` sequential SDD batch contract and `UX-sdd-batch` for batch-origin evidence. Selection supplies no native approval.
