---
id: CAP-EXEC-scheduling-maintenance
title: Scheduling and shared maintenance
summary: "Auto Hub claims due schedules, records bounded task execution, continues installation-wide cleanup and derives verified schedule owners with bounded project filtering. It does not provide a resident timer or exactly-once remote effects."
area: execution
status: active
usecases:
  - UC-run-due-work
entrypoints:
  - modules/hub/app/features/execution/dispatchers/usecases/dispatch.py
  - modules/hub/app/features/scheduling/schedule_configs/api/v1.py
---

# [CAP-EXEC-scheduling-maintenance] Scheduling and shared maintenance

## 1. Summary

An external tick advances due schedule configurations and eligible retries. Shared
maintenance continues pending diagnostic cleanup, provider result collection,
Issue synchronization, SDK flow work and bounded history retention independently
of whether a project or agent schedule remains enabled.

## 2. Scope & Boundary

- **In-Scope**: due-time selection, job checkpoints, async task execution, retry
  eligibility, the installation-owned maintenance schedule and retained history.
- **Out-of-Scope**: the external trigger's delivery cadence, domain-specific PR or
  SDK decisions, provider execution guarantees and notification delivery. The
  dispatcher invokes registered task handlers; their domain contracts own effects.
- **Scope Excluded**: an in-process periodic timer, guaranteed catch-up of every
  missed interval and exactly-once effects across external APIs.

## 3. Business Rules & Policies

1. **Trigger authorization**: WHEN a tick is requested, Hub MUST accept only an
   active signed-in person or a machine key carrying `autohub:dispatch`.
   Test: `modules/hub/tests/integration/auth/test_auth_api.py`.
2. **Due selection**: WHEN selecting schedules, Hub MUST select only enabled rows
   whose `next_run_at` is absent or due and whose optional start/end window includes
   the tick time, within `MAX_DISPATCH_LIMIT`.
   Test: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatcher_services.py`.
3. **Claim checkpoint**: WHEN claiming due schedules, Hub MUST create pending jobs
   and advance schedule timestamps in one transaction before executing handlers.
   Test: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatchers_api.py`.
4. **Retry eligibility**: WHEN selecting retries, Hub MUST select only failed jobs
   with `retry_need=true` and `retry_attempts < retry_max`, excluding configurations
   already selected for a new execution in that tick.
   Test: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatcher_services.py`.
5. **Bounded execution**: WHEN the effective batch timeout elapses, Hub MUST
   cancel unfinished handlers instead of waiting indefinitely.
   Tests: `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services.py`,
   `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services_timeout.py`.
6. **Execution outcome**: WHEN a handler finishes or raises, Hub MUST record its
   job outcome and increment its execution-attempt count; timeout/cancellation
   marks the job retryable, whereas an ordinary exception does not.
   Tests: `modules/hub/tests/integration/features/execution/dispatchers/test_dispatcher_services.py`,
   `modules/hub/tests/unit/features/execution/dispatchers/test_dispatcher_services.py`.
7. **Safe job errors**: IF a task error has no declared operator-safe message,
   THEN Hub MUST keep a generic request-correlated job error rather than persist
   its exception details on the job row.
   Test: `modules/hub/tests/unit/features/execution/dispatchers/test_operator_message.py`.
8. **Maintenance repair**: WHEN startup or a dispatcher tick ensures maintenance,
   Hub MUST repair its singleton `system.maintain` schedule while preserving a
   healthy schedule's due time.
   Test: `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py`.
9. **Managed schedule protection**: WHEN generic schedule mutations target the
   installation-owned maintenance schedule, Hub MUST refuse them with HTTP 409.
   Test: `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py`.
10. **Pending work fairness**: WHILE connection tests and provider catalogs both
   have pending work, maintenance MUST reserve two of its four workers for each
   group and rotate persisted cursors across ticks.
   Test: `modules/hub/tests/integration/features/execution/maintenance/test_fairness.py`.
11. **Failure isolation**: IF one pending maintenance item fails, THEN maintenance
    MUST attempt the other selected items before reporting the aggregated failure.
    Test: `modules/hub/tests/integration/features/execution/maintenance/test_maintenance.py`.
12. **Retention boundaries**: WHEN hourly pruning is eligible, Hub MUST expire
    successful jobs after 3 days, failed jobs after 7 days, terminal PR runs after
    30 days and webhook deliveries after 90 days, while preserving pending work,
    eligible job retries, valid run leases and unresolved Work Item evidence.
    Tests: `modules/hub/tests/integration/features/execution/maintenance/test_retention.py`,
    `modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py`.
13. **Retention transaction**: IF pruning fails, THEN Hub MUST roll back its
    deletions and checkpoint so the next invocation can retry without waiting an
    hour.
    Test: `modules/hub/tests/integration/features/execution/maintenance/test_retention.py`.

14. **Pruning interval**: IF the committed history checkpoint is less than one
    hour old, THEN maintenance MUST skip another pruning pass.
    Test: `modules/hub/tests/integration/features/execution/maintenance/test_retention.py`,
    `test_expired_history_is_pruned_at_most_hourly`.
15. **Job retention clock**: WHEN deciding a terminal job's retention age,
    maintenance MUST use `finished_at` or, for a legacy missing finish time,
    `started_at`.
    Test: `modules/hub/tests/integration/features/execution/maintenance/test_retention.py`,
    `test_pending_and_retryable_jobs_survive_and_retention_uses_finish_time`.
16. **Work Item protection**: IF a linked Work Item lacks succeeded state, a merge
    SHA or completion evidence older than the run-retention boundary, THEN
    maintenance MUST preserve its Run.
    Test: `modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py`,
    `test_retention_requires_durable_success_and_preserves_failed_work`.

17. **Maintained owner clocks**: WHEN a Hub ORM or mapped Core write omits `updated_at`, Hub MUST supply its current UTC write time.
    Explicit business timestamps and same-column preservation expressions take precedence.
    Unchanged ORM flushes and reads do not issue timestamp updates.
    Tests: `modules/hub/tests/integration/common/test_timestamps.py`.
18. **Bookkeeping clocks**: WHEN only acquiring or renewing a PR run lease, claiming a connection-test lease or marking a run notification, Hub MUST preserve its prior `updated_at`.
    Run lease release retains its explicit update to rotate bounded observation batches.
    Tests: `modules/hub/tests/integration/features/project_management/pipeline_runs/test_timestamp_owners.py`.

19. **Verified schedule ownership**: WHEN a public configuration read returns a row, Hub MUST derive its owner and generic mutation flag using the precedence below.
    Test: `modules/hub/tests/integration/features/scheduling/schedule_configs/test_owners.py`.
20. **Project-owned selection**: WHEN project_id filters configuration reads, Hub MUST apply verified owner selection before pagination and counting.
    Test: `modules/hub/tests/integration/features/scheduling/schedule_configs/test_owners.py`.
21. **Bounded owner reads**: WHEN a counted configuration page is read, Hub MUST use at most five SQL statements and one request connection independently of page size.
    Test: `modules/hub/tests/integration/features/scheduling/schedule_configs/test_owners.py`.

## 4. Interfaces & Data Contracts

| Interface | Contract |
| --- | --- |
| `POST /api/v1/dispatchers/trigger` | HTTP 200 with `{"dispatched": <count>}`; count includes claimed schedules and retry jobs, not successful domain outcomes |
| `/api/v1/schedule_configs` and `/{schedule_config_id}` | Create/list/get/patch/put/delete schedule configuration; create/put require exactly one cron expression or interval |
| `/api/v1/schedule_jobs` and `/{schedule_job_id}` | Persisted job history and administrative job operations; a successful job does not itself certify a completed PR |
| `GET /api/health/deep` | Database status plus scheduler `never`, `ok` or `stale` and `last_tick_at`; database failure returns HTTP 503 |
| `system.maintain` | Installation-owned task, empty payload, minimum interval 60 seconds; it runs only when an external tick selects it |

Public list/detail and successful create/patch/put responses include read-only `owner` (`kind`, nullable `project_id`, nullable `object_id`) and `generic_mutation_allowed`. These fields do not authorize writes and are not mutation inputs. `ADR-schedule-owner-projection` owns the derived-read decision.

Apply this precedence top to bottom:

| Condition | owner.kind | Verified IDs | Generic mutations |
| --- | --- | --- | --- |
| system.maintain | system_maintenance | null / null | false |
| pipeline.dispatch_project | project_dispatch | retained payload project / same project | false |
| pipeline.connection_test | connection_test | retained test's project / retained test | false |
| Remaining linked agent schedule | project_agent_schedule | retained schedule's project / agent schedule | false |
| Remaining pipeline.observe_project | project_observation | retained payload project / same project | true |
| Everything else | operator | null / null | true |

Missing, malformed, nonstring and dangling payload references yield null unresolved IDs. Canonical and unhyphenated UUID strings are supported, including uppercase text. A retained test or agent ID can remain known while its project is unresolved. Reserved protection does not depend on resolving an owner. An unlinked provider task is operator-owned.

`GET /api/v1/schedule_configs?project_id=<UUID>` composes with existing search, task, enabled and ordering filters. The count and page use the same correlated owner predicate without duplicate configurations. An unknown project returns an empty counted page; invalid query UUID syntax returns HTTP 422. `skip_count=true` omits the count and returns null total_count. Count/page and at most three bounded owner lookup batches remain sequential in the caller's session; malformed JSON never reaches a database UUID cast. Owner/filter/query-budget regressions exercise SQLite and PostgreSQL with pages of 1 and 50 and retained tests beyond the separate history limit.

Persisted manual-only configurations produced by clearing both triggers remain readable. Create/put trigger validation and existing mutation guards are unchanged.

`ScheduleConfig` owns trigger shape, payload, enabled window and next/last run
instants. `ScheduleJob` owns dispatcher-run identity, outcome, finish time and
retry state. Registered handlers must be asynchronous. Defaults are a dispatch
limit of 200, concurrency of 10 and an effective timeout of 270 seconds
(`GLOBAL_TIMEOUT_SECONDS - GLOBAL_TIMEOUT_BUFFER`); deployment settings can change them.

A run's maintained `updated_at` records its last owner write or observation release, not an exact state-entry or finish event.
A terminal transition obtains a maintained write time before retention reads it.
An old stored value remains unchanged until its next non-exempt write; startup and reads perform no historical backfill.
Raw SQL and reflected tables without Hub's mapped metadata do not receive this application-side update policy.
The SQLite/PostgreSQL owner regression `test_operator_terminal_and_failed_owed_read_use_maintained_time`
verifies that an old run canceled now is retained using its maintained timestamp.

Pruning deletes at most 1,000 jobs and 200 PR runs per invocation. Retiring a run
preserves provider session/report and Work Item completion information, removes
attempt/delivery/reply rows and marks retired links to prevent re-adoption. A
terminal run's age uses `updated_at`; a valid lease prevents deletion. Run expiry
removes its detail/resume surface but does not delete remote PRs, branches or
provider sessions. The retention tests exercise these local-record boundaries;
no remote cleanup is implied.

## 5. Evidence and operational guidance

Sources inspected: `modules/hub/app/features/execution/dispatchers/`,
`modules/hub/app/features/scheduling/schedule_configs/{schemas,services,system}.py`,
`modules/hub/app/features/execution/tasks/domains/maintenance/` and
`modules/hub/app/features/scheduling/schedule_jobs/repos.py`. The tests named above
were inspected as enforcement evidence; this document records no new test run,
production tick or deletion of production history. PostgreSQL lock-concurrency
cases require PostgreSQL and cannot be established by SQLite tests alone.

See [deployment operations](../../operations/cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger)
for external trigger provisioning and [operator diagnostics](../../operations/operator-notices.md)
for inspecting maintenance and retained history.

## 6. Retained activity history

Native graph-based SDD batch admission is retired. Shared maintenance does not
interpret repository workflows or progress native batch phases.
`CAP-SDD-native-delivery` owns optimistic activity claims and retained history.
Retention MUST preserve unresolved claim evidence and its owner link until
explicit settlement; settled claim tombstones prevent old request replay from
creating replacement artifacts. Check: activity-history maintenance tests and
retention source inspection.
