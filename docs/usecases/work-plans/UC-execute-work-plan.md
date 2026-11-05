---
id: UC-execute-work-plan
title: Execute a Work Plan
summary: "An operator registers a batch of specified work and obtains merge-confirmed Item and Plan outcomes while dependencies, scheduling and capacity govern admission. Explicit controls and durable identities preserve unfinished work through interruption."
area: work-plans
primary_actor: Operator
supporting_actors:
  - GitHub
  - Agent provider
  - Repository CI
status: active
capabilities:
  - CAP-WORK-work-plan-execution
  - CAP-PR-pull-request-delivery
entrypoints:
  - modules/hub/app/features/project_management/work_plans/api.py
  - modules/hub/app/features/project_management/work_plans/execution.py
---

# [UC-execute-work-plan] Execute a Work Plan

## 1. Goal

- **Goal**: turn an explicitly specified batch into merged results in dependency
  order, preserving results and unfinished work for review and recovery.
- **Scope**: Auto Hub Work Plan registration, admission and result tracking;
  ordinary PR delivery performs the implementation and merge work.
- **Trigger**: the operator requests execution of specified work before its PRs exist.
- **Preconditions**: the operator can access Hub and has identified the intended
  project. Repository binding, specification completeness, dependencies and
  capacity are checked by Hub rather than assumed.

## 2. Main Success Scenario

1. The operator submits an active batch with specifications, acceptance criteria and dependencies (`CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plans`, `UX-work-plan-editor`.

2. Hub validates and retains the Plan and Item graphs as one registration (`CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plan-editor`, `UX-work-plans`.

3. Hub admits due dependency-ready Items within available capacity (`CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plans`.

4. Hub prepares each admitted Item's branch and PR and delegates its local specification (`CAP-WORK-work-plan-execution`, `CAP-PR-pull-request-delivery`).
   Interface: `UX-work-plans`.

5. Hub carries out PR delivery and observes confirmed merges into the intended target (`CAP-PR-pull-request-delivery`, `CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plans`.

6. Hub releases dependent work and records the Plan complete after all Items succeed (`CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plans`.

7. The operator inspects retained results and any outbound mirror status (`CAP-WORK-work-plan-execution`).
   Interface: `UX-work-plans`.

## 3. Extensions

- **2a.** Invalid graph or incomplete executable specification: Hub rejects the
  write without a partial registration; the operator corrects it and returns to step 1.
  Interface: `UX-work-plan-editor`.

- **2b.** Registration response is lost: the operator recovers the existing Plan
  using the same request identity; resumes at step 3. A changed payload under
  that identity conflicts and the original Plan remains unchanged.
  Interface: `UX-work-plan-editor`.

- **2c.** The operator saves held work: Hub stores draft/proposed/paused work
  without admission. Explicit validated activation resumes at step 3; incomplete
  work remains held.
  Interface: `UX-work-plan-editor`, `UX-work-plans`.

- **3a.** Scheduled time, dependency or capacity is not satisfied: the Item stays
  waiting without premature preparation; resumes at step 3 after all conditions hold.
  Interface: `UX-work-plans`.

- **4a.** An unrelated activity branch exists or the base/attached branch is confirmed absent:
  Hub records `preparation_failed` without overwriting the unrelated branch;
  this Item's execution goal ends and its dependents remain held.
  Interface: `UX-work-plans`.

- **4b.** Remote preparation is uncertain: Hub retains its preparation identity
  and reconciles on continuation; resumes at step 4 without creating duplicate work.
  Interface: `UX-work-plans`.

- **5a.** Run delivery waits or stops: Hub preserves the Item's actual
  Run/PR state; dependents remain held until a correct-target merge is confirmed.
  The operator uses Run control for already-started delivery.
  Interface: `UX-work-plans`.

- **5b.** The PR target/identity changes or its Run disappears: Hub records an
  attention state rather than success; dependent admission remains held and the
  automatic completion path ends pending investigation.
  Interface: `UX-work-plans`.

- **6a.** The operator pauses the Plan: Hub blocks unstarted work while admitted
  work continues; resumes at step 3 after an explicit resume.
  Interface: `UX-work-plans`.

- **6b.** The operator revokes the Plan: Hub permanently withdraws unstarted work
  while admitted work continues; the revoked Plan does not satisfy successful
  dependency completion and the new-admission flow ends.
  Interface: `UX-work-plans`.

- **7a.** Issue mirroring fails or the remote record is edited: Hub retains
  separate mirror/error state without changing execution or dependency outcomes;
  the operator can inspect results while publication reconciles independently.
  Interface: `UX-work-plans`.

- **\*a.** An edit/control uses an obsolete revision: Hub rejects it without
  replacing current work; the operator re-reads and decides whether to retry.
  Interface: `UX-work-plans`.

## 4. Postconditions

- **Success guarantee**: every successful Item retains a confirmed merge to the
  original target; the completed Plan satisfies Plan dependencies. Results remain
  available after eligible detailed Run history expires.
- **Minimal guarantee**: invalid writes do not leave partial graphs; registration
  and preparation identities support recovery. Missing Runs, failed/canceled work
  and remote Issue state are not success evidence. Plan controls do not undo
  already sent provider requests or completed merges.

## 5. Acceptance Criteria (Given / When / Then)

Rules used from `CAP-WORK-work-plan-execution`: graph and registration identity
(1–3), held/complete input (4–6), admission and merge release (7–9), control and
recovery (10–17), mirror independence and retained results (18–19).
`CAP-PR-pull-request-delivery` owns delivery, current-head verification, approval
and merge fencing once a PR is delegated.

### WORK-01: Release only merge-confirmed dependent work

- **Covers**: main success scenario.
- **Given**: two Items where the second depends on the first, and a later Plan depends on this Plan.
- **When**: Hub observes each PR merge into its original target.
- **Then**: the second Item starts from the updated base after the first merge, and the later Plan waits until all predecessor Items succeed.

### WORK-02: Reject an invalid atomic registration

- **Covers**: 2a.
- **Given**: a registration with a cycle, missing Item key or incomplete active Item.
- **When**: the operator submits it.
- **Then**: Hub rejects it and stores no partial executable graph.

### WORK-03: Recover without re-registering different work

- **Covers**: 2b.
- **Given**: a registration whose response was lost and whose Plan has since paused.
- **When**: the original request is replayed, followed by a changed payload under the same identity.
- **Then**: replay returns the same paused Plan and changed work conflicts.

### WORK-04: Hold an incomplete seed until validated activation

- **Covers**: 2c.
- **Given**: an empty draft Plan.
- **When**: activation is requested before and after complete Item specifications are supplied.
- **Then**: incomplete activation is refused, and complete work can be explicitly activated without a second implicit approval gate.

### WORK-05: Enforce the scheduling boundary and other holds

- **Covers**: 3a.
- **Given**: an active Plan scheduled in the future or waiting for dependencies/capacity.
- **When**: a webhook or tick checks eligibility before all conditions hold.
- **Then**: no Item is prepared early; a scheduled Plan does not reserve execution capacity merely by waiting.

### WORK-06: Preserve unrelated branch work

- **Covers**: 4a.
- **Given**: the default activity branch exists and belongs to other work.
- **When**: Hub prepares the new Item.
- **Then**: the Item becomes `preparation_failed`, no PR is created and the existing branch remains untouched.

### WORK-07: Reconcile PR creation after response loss

- **Covers**: 4b.
- **Given**: GitHub created the Item PR but Hub lost the response.
- **When**: preparation is retried.
- **Then**: Hub links the existing PR and Run, retaining one PR for that Item preparation.

### WORK-08: Preserve failed work and its dependent hold

- **Covers**: 5a.
- **Given**: an Item Run was canceled and its PR closed without merging.
- **When**: Hub observes the result.
- **Then**: the Item is not successful and its dependent Item remains waiting.

### WORK-09: Refuse wrong-target or missing-Run success

- **Covers**: 5b.
- **Given**: an Item PR merged into a changed target or its linked Run is unexpectedly absent.
- **When**: Hub observes completion.
- **Then**: the Item requires attention and its dependents remain waiting.

### WORK-10: Control only unstarted work

- **Covers**: 6b.
- **Given**: one admitted Item and one waiting dependent Item.
- **When**: the operator revokes the Plan and the admitted PR later merges.
- **Then**: the admitted Item records success, the waiting Item remains revoked and the Plan stays revoked.

### WORK-11: Keep Issues outside execution authority

- **Covers**: 7a.
- **Given**: Issue creation fails or published Issues are edited and closed remotely.
- **When**: Hub advances the Plan.
- **Then**: eligible work can still execute and remote Issue changes do not release dependencies.

### WORK-12: Refuse a stale control

- **Covers**: \*a.
- **Given**: the operator inspected an earlier Plan revision.
- **When**: a control is submitted with that obsolete revision.
- **Then**: Hub returns a conflict without applying the stale control.

### WORK-13: Resume only waiting work after a Plan pause

- **Covers**: 6a.
- **Given**: admitted work and an unstarted Item in a paused Plan.
- **When**: admitted work finishes before the operator resumes the Plan.
- **Then**: the waiting Item remains unstarted until resume rechecks admission; existing Runs are not restarted.

## 6. Evidence boundary

The scenarios derive from the inspected source and named tests in
`CAP-WORK-work-plan-execution`, including `test_work_plans.py`,
`test_registration.py`, `test_backlog.py`, `test_scheduling.py` and
`test_review_regressions.py`. The PR portion uses the evidence listed in
`CAP-PR-pull-request-delivery`. No tests or live provider calls were executed
while authoring this use case; these examples do not establish deployment or an
SDD adoption baseline.
