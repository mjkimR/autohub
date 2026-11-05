---
id: UC-run-agent-session
title: Run a Scheduled Agent Session
summary: "An operator runs Jules task or report work through a project-owned agent schedule and reviews its retained result. The schedule makes work due for dispatch; report completion and task pull request adoption have distinct outcomes."
area: agents
primary_actor: Operator
supporting_actors:
  - Jules
  - GitHub
status: active
capabilities:
  - CAP-AGENT-provider-sessions
entrypoints:
  - modules/hub/app/features/project_management/agent_schedules/api/v1.py
  - modules/hub/app/features/execution/tasks/domains/jules/task.py
  - modules/hub/app/features/execution/tasks/domains/jules/service.py
---

# [UC-run-agent-session] Run a Scheduled Agent Session

## 1. Goal

- **Goal**: obtain the selected project agent's task deliverable or report through a tracked session, so its result can be reviewed independently of the scheduler job.
- **Scope**: project-owned Jules session schedules and completion collection.
- **Trigger**: the operator wants scheduled work to run before its next regular due time.
- **Preconditions**: the operator has access to Hub's project agent-schedule management API.

## 2. Main Success Scenario

1. The operator submits a project schedule for the intended task work (`CAP-AGENT-provider-sessions`).
2. Hub validates the schedule and derives its owned session scheduler entry (`CAP-AGENT-provider-sessions`).
3. The operator requests that the enabled schedule run at the next opportunity (`CAP-AGENT-provider-sessions`).
4. Hub dispatches the due session after provider preflight and catalog admission (`CAP-AGENT-provider-sessions`).
5. Hub collects the provider's completed task and its PR evidence (`CAP-AGENT-provider-sessions`).
6. Hub adopts the eligible task PR into the connected project's normal delivery workflow (`CAP-AGENT-provider-sessions`).
7. The operator reviews the session result and linked delivery run (`CAP-AGENT-provider-sessions`).

## 3. Extensions

- **1a.** Existing schedule: the operator selects or updates an existing suitable schedule; resumes at step 3.
- **2a.** Invalid schedule or unsupported catalog: Hub refuses with HTTP 422; domain refusals use `INVALID_REQUEST`, while invalid request fields use schema-validation output; the use case ends without saving the invalid mutation.
- **3a.** Disabled owned entry: Hub refuses run-now with HTTP 422 `INVALID_REQUEST`; the use case ends without making it due.
- **3b.** Missing owned entry: Hub refuses run-now with HTTP 409 `CONFLICT` and directs the operator to save the schedule again; the use case ends.
- **4a.** Credentials or repository Source unavailable: the session task fails preflight without reserving a new dispatch or creating a session; the use case ends without a new deliverable.
- **4b.** Catalog admission refused: the task reports HTTP 409 `CONFLICT` internally while retaining the catalog's policy state; the use case ends without creating a tracked/provider session for that invocation.
- **4c.** Provider create result uncertain: the task reports the create failure while retaining its unconfirmed session; collection reconciles the original title without repeating that stored create; resumes at step 5 if found, or ends with a failed presumed-lost session after a qualifying later observation.
- **4d.** Definitive provider create refusal: Hub records the session as failed, including a catalog hold for HTTP 429; the use case ends without a deliverable.
- **5a.** Provider waits for human input: Hub records the stalled session as failed and releases its open-session capacity; resumes at step 7 with failure detail instead of a deliverable.
- **5b.** Provider observation temporarily fails: Hub defers observation to subsequent collection; resumes at step 5 without claiming completion.
- **6a.** Report work selected: Hub stores the final session message rather than enrolling a PR; resumes at step 7 without a pipeline run.
- **6b.** Final message unavailable: Hub keeps the completed session with an empty summary rather than a guessed partial result; resumes at step 6 for task adoption or step 7 for a report.
- **6c.** Task PR missing or ineligible: Hub stores a diagnostic without creating a pipeline run; resumes at step 7 with the completed provider state and incomplete delivery outcome.
- **6d.** PR already enrolled: Hub links the existing active run for that project/PR; resumes at step 7.
- **6e.** Adoption interrupted before a verdict: later collection retries the pending adoption; resumes at step 6.
- **6f.** Adoption error recorded: Hub stores its diagnostic without stopping other session collection or blindly retrying that verdict; resumes at step 7 without a run.
- **\*a.** Unknown/project-mismatched schedule: Hub refuses with HTTP 404 `NOT_FOUND`; the use case ends.

## 4. Postconditions

- **Success guarantee**: the task's eligible PR is linked to normal project delivery, or the report's available final message is retained without creating a pipeline run; normal PR approval/CI/merge policy remains applicable.
- **Minimal guarantee**: an accepted run-now only changes due state, refused preflight/admission creates no new session, an unconfirmed stored create is reconciled rather than replayed, and incomplete results remain distinguishable from successful delivery.

## 5. Acceptance Criteria (Given / When / Then)

Rules used from `CAP-AGENT-provider-sessions`: **Supported session kind**,
**Repository prerequisite**, **Owned scheduler entry**, **Run-now meaning**,
**Source preflight**, **Admission before creation**, **Tracked dispatch identity**,
**Unconfirmed reconciliation**, **Provider quota refusal**, **Stalled sessions**,
**Report deliverable**, **Unproven report text**, **Task adoption**,
**Adoption boundary**, **Adoption recovery**, **Existing adoption**,
**Recorded adoption failure**.

### Scenario SESSION-01: Adopt a completed task

- **Covers**: main success scenario.
- **Given**: valid Jules credentials, repository Source and capacity, plus an enabled project permitting session adoption.
- **When**: the operator makes a valid task schedule due and the dispatched session completes with an eligible PR.
- **Then**: the session retains its provider result and an already-implemented delivery run is linked; this does not itself prove CI success or merge.

### Scenario SESSION-02: Reuse a configured schedule

- **Covers**: 1a.
- **Given**: an existing suitable project schedule.
- **When**: the operator changes its valid title/prompt and requests run-now.
- **Then**: the owned entry is rewritten and made due without creating a second schedule entry.

### Scenario SESSION-03: Refuse invalid schedule setup

- **Covers**: 2a.
- **Given**: a project without a repository, a Codex catalog, a newly selected disabled catalog, or invalid trigger settings.
- **When**: the operator submits the schedule.
- **Then**: HTTP 422 is returned and the invalid definition is not saved.

### Scenario SESSION-04: Refuse a paused run-now

- **Covers**: 3a.
- **Given**: the schedule's owned entry is disabled by the schedule, project or catalog.
- **When**: the operator requests run-now.
- **Then**: HTTP 422 `INVALID_REQUEST` is returned and no session is started synchronously.

### Scenario SESSION-05: Diagnose a missing owned entry

- **Covers**: 3b.
- **Given**: an agent schedule whose scheduler entry is absent.
- **When**: the operator requests run-now.
- **Then**: HTTP 409 `CONFLICT` directs the operator to save the schedule again.

### Scenario SESSION-06: Fail provider preflight without reservation

- **Covers**: 4a.
- **Given**: a missing Jules connector or no matching Source for the session repository.
- **When**: the due session task executes.
- **Then**: it fails before creating a tracked/provider session; failed Source resolution reserves no dispatch.

### Scenario SESSION-07: Respect catalog admission

- **Covers**: 4b.
- **Given**: a Jules catalog whose daily task limit is exhausted.
- **When**: the due task requests admission.
- **Then**: its failure carries `CONFLICT`, the quota hold remains recorded, and no new tracked session or provider POST exists.

### Scenario SESSION-08: Reconcile an unconfirmed creation

- **Covers**: 4c.
- **Given**: a stored dispatching session with no provider name after an uncertain create result.
- **When**: later collection searches provider sessions by its unique title.
- **Then**: a matching session is attached without repeating its stored create; if absent at an observation at least one hour after creation, the row is failed as presumed lost.

### Scenario SESSION-09: Preserve provider quota refusal

- **Covers**: 4d.
- **Given**: an admitted session whose provider create request returns HTTP 429.
- **When**: Hub records the refusal.
- **Then**: the session is `failed` and the catalog has a quota hold.

### Scenario SESSION-10: Fail a provider session that needs input

- **Covers**: 5a.
- **Given**: a tracked session observed in `awaiting_plan_approval`, `awaiting_user_feedback` or `paused`.
- **When**: Hub applies that observation.
- **Then**: it records `failed` with the waiting-state diagnostic and releases open-session capacity.

### Scenario SESSION-11: Defer an unreadable provider observation

- **Covers**: 5b.
- **Given**: an unfinished session whose provider lookup raises a request error.
- **When**: collection encounters the error.
- **Then**: the stored session remains unfinished for a later observation and collection does not POST another creation for it.

### Scenario SESSION-12: Keep a report in its session

- **Covers**: 6a.
- **Given**: a report schedule whose provider session completes with a readable final message.
- **When**: Hub collects completion.
- **Then**: `result_summary` retains that message and no pipeline run is created.

### Scenario SESSION-13: Leave incomplete report evidence empty

- **Covers**: 6b.
- **Given**: a completed session with an unreadable activity log or a log exceeding the complete-read page budget.
- **When**: Hub collects its final message.
- **Then**: the provider state remains `completed` and the summary is null instead of an intermediate message.

### Scenario SESSION-14: Retain an unadoptable task outcome

- **Covers**: 6c.
- **Given**: a completed task with no PR, a PR in another repository, or an opted-out project.
- **When**: Hub evaluates its deliverable.
- **Then**: the row retains `completed` and a diagnostic without a pipeline run.

### Scenario SESSION-15: Link existing PR delivery

- **Covers**: 6d.
- **Given**: the task PR already has an active run in its connected project.
- **When**: task adoption encounters that enrollment.
- **Then**: the session links that run without creating another.

### Scenario SESSION-16: Recover adoption after interruption

- **Covers**: 6e.
- **Given**: a completed task row with a PR but neither run nor adoption diagnostic.
- **When**: collection runs after the interruption.
- **Then**: it retries that pending adoption and records the resulting run or verdict.

### Scenario SESSION-17: Isolate recorded adoption errors

- **Covers**: 6f.
- **Given**: task enrollment raises an unexpected error.
- **When**: Hub records the adoption outcome.
- **Then**: that session stores the diagnostic, other session collection continues, and the recorded failure is not blindly retried.

### Scenario SESSION-18: Reject a schedule outside the project

- **Covers**: *a.
- **Given**: an unknown schedule or a schedule belonging to another project.
- **When**: the operator requests its project-scoped operation.
- **Then**: HTTP 404 `NOT_FOUND` is returned.

The source and existing tests listed in `CAP-AGENT-provider-sessions` ground these
scenarios. The lost-create timeout, missing-entry refusal and observation-error
handling are source-inspected branches; no new execution coverage is claimed.
No live Jules execution or successful provider obedience to prompts is inferred
from scheduler configuration or automated fixtures.
