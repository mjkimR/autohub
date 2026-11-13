# Timestamp write evidence

Source: `e1a50a8064597d65fd44906f1b65c01ad93c2425`, observed on 2026-11-13 in the assigned Planning worktree.
No production deployment or production database was inspected.

## Mechanism probe

The installed app-layer-base `TimestampMixin` has `server_default=func.now()` and `server_onupdate=func.now()`,
with no client `onupdate`. SQLAlchemy is 2.0.52. A synchronous in-memory SQLite probe defined one minimal mapped
owner using that mixin and one using its subclass with `onupdate=get_current_utc_time`. Each row started at a
controlled 2000-01-01 timestamp. No repository source or dependency was modified.

| Probe | Installed mixin | Candidate override |
| --- | --- | --- |
| ORM changes a string field and commits | Timestamp unchanged (defect reproduced) | Timestamp advances |
| Core `update(Model).values(value=...)` | Timestamp unchanged (defect reproduced) | Timestamp advances |
| Core explicitly supplies `updated_at=Model.updated_at` | Timestamp preserved | Timestamp preserved |

All six observations completed with exit 0. The probe's source shape was a `DeclarativeBase`, two mapped tables,
`create_engine('sqlite:///:memory:')`, Session ORM updates, then the two Core statements above. Values were refreshed
after each commit. The current and candidate mixins shared `DateTime(timezone=True)` and insertion server defaults.
This isolates the `onupdate` distinction; it does not test Hub HTTP/use-case behavior or PostgreSQL.

The [official SQLAlchemy defaults documentation](https://docs.sqlalchemy.org/en/20/core/defaults.html)
confirms that a column default is used when that particular column is omitted, even if other columns are supplied.
The installed compiler implements this in `sqlalchemy/sql/crud.py` `_append_param_update`: `onupdate` renders or
prefetches a value, while `server_onupdate` only requests fetching. The draft's former statement that all explicit
Core values bypass `onupdate` was incorrect.

## Inventory

An AST scan of `modules/hub/app/**/*.py` found 47 direct `TimestampMixin` classes across 18 files. This confirms the
proposal's count for this source HEAD. They include configuration, scheduling, flows, task state, notifications,
AI catalogs, project/agent/connection records, delivery records, SDD batches/claims and Work Plan/replacement/template
records. Models without the timestamp mixin, such as decision/discovery projections, remain outside coverage.

The same scan found 22 SQLAlchemy `update(Model)` calls:

| Owning file under `modules/hub/app/features/` | Methods and models | Timestamp direction |
| --- | --- | --- |
| `execution/dispatchers/services.py` | `get_retry_jobs`, `_run_dispatch`: ScheduleJob | Default maintained write time |
| `execution/flows/repos.py` | `bump`: FlowRun; `activate`: FlowEnvironment | Keep explicit caller timestamp |
| `execution/flows/repos.py` | `claim`, `release_lease`: FlowRun | Default last-write time; not an owed owner |
| `execution/tasks/domains/maintenance/history.py` | `delete_runs`: AICatalogSession, WorkItem, SddActivityClaim | Default maintained retirement/link-removal write time |
| `project_management/github_webhooks/repos.py` | `claim`: GitHubWebhookDelivery | Default maintained retry-state change time |
| `project_management/work_plans/execution_repo.py` | `claim`: WorkItem | Default maintained last-write time, including retry scheduling |
| `project_management/work_plans/issue_sync.py` | `execute`: WorkIssueMirror | Default maintained last-write time |
| `project_management/projects/services.py` | `update`: PipelineRun project_revision | Default maintained owner write time |
| `project_management/projects/repos.py` | `save_check`: Project | Default maintained check-result write time |
| `project_management/connection_tests/repos.py` | `claim`: ConnectionTest | Explicitly preserve pure lease claim |
| `project_management/connection_tests/repos.py` | `finish_step`: ConnectionTest | Keep explicit caller timestamp |
| `project_management/connection_tests/repos.py` | `cancel`: ConnectionTest | Default maintained cancellation-request write time |
| `project_management/pipeline_runs/repos.py` | `acquire_lease`, `renew_lease`: PipelineRun | Explicitly preserve pure lease operations |
| `project_management/pipeline_runs/repos.py` | `release_lease`: PipelineRun | Keep explicit caller timestamp for existing observation fairness |
| `project_management/pipeline_runs/repos.py` | `mark_stop_announced`: PipelineRun | Keep explicit same-column preservation |
| `scheduling/schedule_configs/system.py` | `ensure_maintenance_schedule`: ScheduleConfig | Default maintained time for a repair UPDATE; healthy config emits none |

`pipeline_runs/discovery_projection.py` uses `table.update()` on a timestamp-free projection. No `on_conflict_do_update`
or textual owner UPDATE was found by the application search. Inserts with `on_conflict_do_nothing` do not update a row.
Raw SQL from an external writer is not covered by a Python-side mapped-column default.

## Reader and rotation constraints

`owed_items/repos.py` uses owner `updated_at` for failed/stopped runs, proposed Plans, attention Items, replacement
links and attention SDD batches. Decision entries use their own `waiting_since`; recoveries use creation;
ConnectionTests prefer `finished_at`. `CAP-PR-owed-items` explicitly keeps no state-entry time.

`pipeline_runs/repos.py:list_active` sorts observing/uncertain runs by `updated_at` to rotate bounded batches.
`release_lease` writes `updated_at=now` even when an observation yields no workflow progress.
`usecases/advancement.py` always attempts that release in `finally`. Preserving the release time without replacing
its scheduling role would change fairness. `mark_stop_announced` deliberately writes its old timestamp and must
keep that exception. Thus this repair cannot promise exact state-entry or exact finish-event times.

`maintenance/history.py:delete_runs` selects terminal run age by `updated_at`. It retires related links and preserves
unresolved claims/unsuccessful Items before deletion. Those retention rules and windows remain unchanged.
The existing regression fixtures manually assign age; Development needs a real operator cancellation/write test.

## Remaining verification

Only the minimal SQLite mechanism probe ran during Planning. No Hub regression suite, PostgreSQL clock/concurrency
check, lint/build or live service check ran. Development must test UTC serialization, ORM refresh/expiration,
actual owner writes, explicit exceptions, mixed business/lease writes and observation fairness on its final HEAD.
Historical true update times are not reconstructible from the inventory and will not be backfilled.
