---
id: CAP-AGENT-provider-sessions
title: Scheduled Provider Sessions and Deliverables
summary: "Project agent schedules start tracked Jules task or report sessions through catalog admission and retain their completion evidence. Completed task pull requests may enter normal project delivery, while reports remain session messages and collection is independent of schedule enablement."
area: agents
status: active
usecases:
  - UC-run-agent-session
entrypoints:
  - modules/hub/app/features/project_management/agent_schedules/api/v1.py
  - modules/hub/app/features/project_management/agent_schedules/services.py
  - modules/hub/app/features/execution/tasks/domains/jules/task.py
  - modules/hub/app/features/execution/tasks/domains/jules/service.py
---

# [CAP-AGENT-provider-sessions] Scheduled Provider Sessions and Deliverables

## 1. Summary

An operator-owned project agent schedule starts recurring Jules work against the
project repository. Hub tracks provider sessions separately from the scheduler job
and delivers either a stored report or a link to an adopted implementation PR.

## 2. Scope & Boundary

- **In-Scope**: project schedule ownership, due-time controls, Jules session
  preflight and creation, uncertain-create reconciliation, collection, report
  retention, completed-task PR adoption and stalled-session handling.
- **Out-of-Scope**: quota/capacity decisions belong to
  `CAP-AGENT-catalog-admission`; adopted-PR CI, repairs, approval and merge belong
  to `CAP-PR-pull-request-delivery`; isolation checks belong to
  `CAP-CONN-connection-verification`; provider execution belongs to Jules.
- **Scope Excluded**: scheduled Codex sessions, answering provider plan/questions,
  stopping already running provider work by disabling a schedule, a direct
  session-start REST endpoint, or guaranteeing provider obedience to report prompts. Applying Jules
  `changeSet.gitPatch` to an existing PR, writing report messages into repository
  history, provider callbacks and automatic catalog routing are not implemented.

## 3. Business Rules & Policies

1. **Supported session kind**: IF a selected catalog cannot run the requested scheduled work type, THEN Hub MUST refuse schedule creation with HTTP 422 `INVALID_REQUEST`. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_a_catalog_without_session_work_is_refused`.
2. **Repository prerequisite**: IF a project has no GitHub repository, THEN Hub MUST refuse its agent schedule with HTTP 422 `INVALID_REQUEST`. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_a_project_without_a_repository_cannot_schedule_sessions`.
3. **Owned scheduler entry**: WHEN an agent schedule is created, Hub MUST derive only its corresponding session scheduler entry without creating a per-catalog synchronization entry. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_creating_a_schedule_derives_only_its_session_entry`.
4. **Ownership protection**: WHEN a generic schedule mutation targets an agent-owned entry, Hub MUST refuse mutation with HTTP 409 `CONFLICT`. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_the_generic_schedule_api_refuses_to_touch_an_owned_entry`.
5. **Effective enablement**: WHILE the agent schedule, its project or its catalog is disabled, or the project lacks its repository, Hub MUST keep the owned session entry disabled. Tests: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_disabling_the_catalog_pauses_its_agent_schedules` and `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_disconnecting_the_project_from_github_pauses_its_agent_schedules`.
6. **Fresh due time**: WHEN the trigger changes or an owned entry becomes enabled again, Hub MUST recompute its next due time rather than execute from a retained stale due time. Tests: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_updating_rewrites_the_entry_and_a_trigger_change_recomputes_the_next_run` and `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_re_enabling_a_schedule_recomputes_its_next_run`.
7. **Run-now meaning**: WHEN run-now is accepted, Hub MUST make the enabled scheduler entry due for its next dispatcher tick instead of synchronously starting a provider session. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_run_now_makes_the_entry_due_immediately`.
8. **Schedule deletion**: WHEN an agent schedule is deleted, Hub MUST remove its owned session entry without deleting an operator-owned synchronization entry. Test: `modules/hub/tests/integration/features/project_management/agent_schedules/test_agent_schedules_api.py::test_an_operator_sync_entry_for_the_catalog_is_left_alone`.
9. **Source preflight**: IF Jules cannot resolve the repository's actual Source resource before admission, THEN Hub MUST fail the start without reserving a dispatch or creating a tracked/provider session. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_source_preflight_failure_does_not_reserve_or_create_a_session`.
10. **Admission before creation**: IF shared catalog admission rejects a session, THEN Hub MUST retain any policy hold without creating its session record or calling provider creation. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_reaching_the_daily_limit_holds_the_catalog_without_creating_a_session`.
11. **Tracked dispatch identity**: WHEN session admission succeeds, Hub MUST persist the tracked session and `session:{session_id}` ledger identity before its provider create request. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_an_admitted_session_is_created_counted_and_tracked`.
12. **Unconfirmed reconciliation**: WHEN synchronization encounters a session without a provider name, Hub MUST search recent provider sessions by its unique title rather than repeat that stored creation attempt. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_sync_adopts_an_unconfirmed_session_and_releases_a_finished_one`.
13. **Provider quota refusal**: WHEN provider creation returns HTTP 429, Hub MUST mark the tracked session failed and record the catalog quota event. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_rate_limited_create_fails_the_session_and_holds_the_catalog`.
14. **Stalled sessions**: WHEN Jules reports `awaiting_plan_approval`, `awaiting_user_feedback` or `paused`, Hub MUST record a failed session instead of retaining a slot for input Hub cannot provide. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_session_waiting_for_a_person_is_failed_and_releases_its_slot`.
15. **Report deliverable**: WHEN collection observes a completed report session with a readable final agent message, Hub MUST store that message without enrolling a PR or creating a pipeline run. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_completed_report_session_keeps_its_final_message_and_opens_nothing`.
16. **Unproven report text**: IF the completion activity log is unreadable or exceeds the complete-log page budget, THEN Hub MUST leave `result_summary` empty rather than substitute a partial message. Tests: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_an_unreadable_activity_log_leaves_the_summary_empty` and `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_final_message_past_the_page_budget_is_not_guessed`.
17. **Task adoption**: WHEN collection observes a completed task with an eligible PR in its session repository and an enabled project permitting session adoption, Hub MUST enroll the PR as already implemented. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_completed_task_session_has_its_pull_request_adopted_as_implemented`.
18. **Adoption boundary**: IF a task has no PR, its PR belongs to another repository, or its project disables session adoption, THEN Hub MUST retain the completion with a diagnostic instead of creating a pipeline run. Tests: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_task_session_without_a_pull_request_is_noted`, `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_pull_request_outside_the_session_repository_is_not_adopted` and `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_project_can_opt_out_of_adopting_session_pull_requests`.
19. **Adoption recovery**: WHEN a completed task has a PR but no adoption verdict after an interruption, Hub MUST reconsider it during subsequent collection. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_adoption_left_unfinished_by_a_crash_is_retried_on_the_next_sync`.
20. **Existing adoption**: WHEN PR enrollment finds an existing active run for the same project/PR, Hub MUST link that run to the session instead of creating another one. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_a_pull_request_enrolled_by_someone_else_is_linked_to_the_session`.
21. **Recorded adoption failure**: IF adoption raises an unexpected error, THEN Hub MUST record its diagnostic on that session without stopping other session collection. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_an_unexpected_adoption_error_is_recorded_and_does_not_stop_the_sync`.
22. **Independent collection**: WHEN pending provider sessions or adoption work exist without enabled agent schedules, Hub MUST collect that work through shared maintenance without starting additional provider sessions. Test: `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py::test_pending_sessions_are_collected_without_agent_schedules_and_failures_are_isolated`.

## 4. Interfaces & Data Contracts

Project schedule base: `/api/v1/projects/{project_id}/agent-schedules`.

| Method and suffix | Contract |
| --- | --- |
| `GET` collection | `{items: AgentScheduleRead[]}` |
| `POST` collection | Valid `AgentScheduleWrite`; HTTP 201 |
| `GET /{schedule_id}` | Reads the project-scoped schedule |
| `PUT /{schedule_id}` | Replaces schedule settings and rewrites its owned entry |
| `DELETE /{schedule_id}` | Removes schedule and owned entry; HTTP 204 |
| `POST /{schedule_id}/run-now` | Makes its enabled entry due; returns the schedule, not a provider session |

`AgentScheduleWrite` requires `ai_catalog_id`, `title` (1–200 characters) and
`prompt` (1–20000 characters). `work_type` is `task` (default) or `report`;
`starting_branch` defaults to `main` (1–255 characters); `enabled` defaults true.
Exactly one valid `cron_expression` (up to 100 characters) or `interval_seconds`
(60–2592000) is required. Extra fields and blank trimmed titles are rejected.
Only Jules currently maps to the `jules.session` scheduler task. Existing
schedules remain editable on their disabled current catalog; newly selecting a
disabled catalog is refused. Project changes rewrite repository/name/enablement
in owned entries. Schedule reads include their entry ID, due/last-run times and
up to five recent sessions.

Run-now refuses missing owned entries with HTTP 409 `CONFLICT` and disabled
entries with HTTP 422 `INVALID_REQUEST`. Unknown/project-mismatched schedules
return HTTP 404 `NOT_FOUND`. Schema-validation HTTP 422 is distinct from domain
`INVALID_REQUEST`. Generic owned-entry updates/deletes return HTTP 409.

`jules.session` requires a scheduler task context. It accepts `JulesSessionPayload`:
`catalog_key` (default `personal-jules`), GitHub `repository`, `starting_branch`,
`title`, `prompt`, `work_type` and optional `auto_create_pr`.
Task work defaults `auto_create_pr=true`; report work defaults false and forbids
true. The appended prompt requests one new-branch PR for task work and a final
session message without commits/branches/PRs for reports; these are provider
instructions, not a guarantee that external execution cannot violate them.

Before starting, Hub requires a Jules catalog with an enabled Jules connector
whose decrypted credentials contain a nonblank `token`. It refreshes tracked
sessions, resolves the real Jules Source, then attempts catalog admission.
A tracked session's unique title contains `[hub-session:{session_id}]`.
The provider client sends `requirePlanApproval=false` and either `AUTO_CREATE_PR`
or `AUTOMATION_MODE_UNSPECIFIED` according to the payload.

An immediately terminal creation response is stored by the creation path.
Final-message collection and PR adoption are specified for completion observed
during collection; the immediate-terminal creation edge has no dedicated
inspected regression establishing those deliverables.

Each session task invocation creates a separate work unit. An uncertain create
keeps its stored row in `dispatching`; synchronization searches at most three
100-entry provider pages for its title. If still absent at an observation at least
one hour after creation, source `_observe` marks the row failed as presumed lost.
Provider request failures during observation are deferred to later collection;
they do not authorize another POST for that stored row. Definitive non-5xx create
refusals mark it failed; service errors use status 422/429 when applicable and
502 otherwise. These task/service errors are not a session-start REST response.

Provider session states are normalized to lowercase; `completed` and `failed`
release open-session capacity. `jules.sync_sessions` collects without creating
work; shared maintenance also collects unfinished sessions and pending task
adoptions even after their schedules/catalogs are disabled, subject to usable
provider credentials. Completion reads at most 50 activity pages of 100 entries,
keeping the last nonblank agent message only if the entire log was read. A failed
completion-message read remains empty rather than being automatically retried.

A completed task retains its PR URL and optional `pipeline_run_id`. Adoption
requires a same-repository GitHub PR URL and a connected enabled project with
`automation.auto_enroll_sessions` true (default). It calls normal enrollment with
`implemented=true`; later PR actions remain subject to `CAP-PR-pull-request-delivery`.
Provider HTTP 429 is conservatively treated as a quota event; Hub does not infer
whether the remote limit was daily quota or concurrency. Counting `sendMessage`
or repeated PR comments as daily tasks, and provider queueing at the concurrency
limit, are not established by the inspected source or tests.
A recorded adoption diagnostic prevents blind retries; an interruption before a
verdict is recorded remains recoverable. Expired adopted runs set
`pipeline_run_retired_at`, preventing automatic readoption.

Session listings use `GET /api/v1/ai-catalogs/{catalog_key}/sessions` and retain
`work_type`, provider state/name/URL, PR URL, optional pipeline link, summary,
failure detail and last observation. Schedule deletion does not cancel external
work; collected session records remain separately owned.

## 5. Implementation and Verification Sources

The contract is derived from the listed entrypoints plus
`modules/hub/app/features/project_management/agent_schedules/{schemas.py,repos.py}`,
`modules/hub/app/features/ai_catalogs/{models.py,repos.py,providers/jules.py}`
and shared maintenance. Existing integration tests cited above exercise the
contracts; payload mode tests are in
`modules/hub/tests/unit/features/execution/tasks/domains/jules/test_service.py`.
The one-hour lost-create timeout is source-inspected in `JulesSessionService._observe`;
the cited reconciliation test does not independently exercise that timeout.
These references report source/test inspection, not a fresh test execution or
live provider run. Detailed procedures remain in
[provider connections](../../operations/provider-connections.md).
