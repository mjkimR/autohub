# Owed-state inventory (Planning evidence, scout round 1)

Persisted state that marks each candidate kind as waiting for the operator, at the Planning worktree HEAD. Paths are
relative to `modules/hub/app/features/` unless they start with `docs/` or `modules/`.

| Kind | Waiting predicate | Storage and index | Cross-project read today | Natural key |
| --- | --- | --- | --- | --- |
| Decision-inbox rows | `run_decision_entries.actionable = true` and run state not final | Projection table, refreshed by mapper hooks on PipelineRun, RunQuestion, RunResumeReceipt inside the owner transaction; indexes on (waiting_since, key), (project_id, waiting_since, key), (kind, waiting_since, key); none on `actionable` (`project_management/pipeline_runs/models.py:207-228`, `discovery_projection.py:120-127`) | Yes: `GET /api/v1/pipeline-runs/decisions`, `actionable_total_count` (`discovery_repo.py:10-46`) | `decision_key = <run_id>:<digest(kind, subject)>`; `fingerprint` changes with content (`discovery_projection.py:51-101`) |
| PR runs paused / blocked | `state in (paused, blocked)`; reasons only in free-text `pause_reason`; no actor, `paused_by`, acknowledgement or dismissal field (`pipeline_runs/models.py:12-57, 96-107`) | `state` indexed | Dashboard counts only (`dashboard/repos.py:11-36`) | run id |
| Held by a decision | `blocked` with an open or answered RunQuestion, or paused/blocked native run with projection rows (`interaction_service.py:73-94`, `sdd/discovery.py:7-61`) | Join to projection | Via decisions list | decision key |
| Operator pause | `paused`, `pause_reason` = request reason or literal "Manually paused by user" (`usecases/control.py:51-67`) | Not distinguishable from system pauses (CI failure, merge gating: `usecases/ci.py:173-186, 248-249, 284-285`) without text matching | - | run id |
| Dismissed question | run stays `blocked`, question `dismissed`, no decision row (`usecases/interactions.py:138-150`) | - | Dashboard blocked count only | run id |
| PR runs failed | `state = failed`, final: pause, cancel and resume reject it (`usecases/control.py:133, 311-312, 368-381`); leaves only through Work Item recovery activation (`usecases/recovery.py:24, 79-81`); pruned after 30 days (`execution/tasks/domains/maintenance/retention.py:11`) | `state` indexed | Dashboard counts only | run id |
| Work Plans proposed | `work_plans.state = proposed` (`work_plans/models.py:21-41`, `services.py:152-178`) | No `state` index | Per project only (`work_plans/api.py:22,25`) | plan id |
| Work Item recovery | `WorkItemRecovery.state in (accepted, reconciling, awaiting-admission)`; awaiting-admission is a system hold (`work_plans/models.py:131-169`, `recovery.py:20`) | Partial unique index on item_id where pending; no project_id index | Per project only | recovery id |
| Replacement / dependency acceptance | Booleans `ReplacementLink.active`, `ReplacementAcceptance.active/consumed`; waiting is derived, not stored (`work_plans/replacement_models.py:17-66`) | Partial unique indexes on active | Per project only | link id |
| Work Item `attention` | `WorkItem.state = attention` (native SDD items, missing run) (`work_plans/execution.py:179-217`) | `state` indexed | Per project only | item id |
| SDD batch attention | `sdd_batches.state = attention` (`sdd/batch_models.py:11-32`, `batch_driver.py:357-405`) | No `state` index | Per project, 50 rows (`sdd/batch_repo.py:26-34`) | batch id |
| Connection-test cleanup review | terminal status, `cleanup_status != completed`, evidence keys and an adapter flag found in code (`connection_tests/recovery.py:12-21`) | No `cleanup_status` index; not a pure SQL predicate | Per project only | test id |
| AI catalog hold | `availability_state in (disabled, unknown)` or `quota_blocked` with future/absent `available_at`; mostly policy holds that expire (`ai_catalogs/services.py:37-45, 160-177`) | `available_at` indexed; no run field records "blocked by catalog" | Catalog list | catalog id |

## Related facts

- `PipelineRun` and `PipelineRunRead` carry no origin column (Work Item, Work Plan, SDD batch, provider session,
  enrollment source). Links exist only on the other side: `WorkItem.pipeline_run_id`, `AICatalogSession.pipeline_run_id`,
  `SddActivityClaim.run_id` (`pipeline_runs/schemas.py:68-88`).
- Dashboard Needs-you: `GET /api/v1/dashboard/stats` counts every PipelineRun by state with no project filter; the UI
  sums failed + paused + blocked (`modules/hub-ui/src/lib/features/dashboard/dashboard.svelte.ts:48-59`).
- Decision notices: maintenance tick scans actionable projection rows, dedupes on (decision_key, fingerprint), link
  `/decisions?decision_key=&decision_fingerprint=`; subscribable kinds are only the decision kinds
  (`notifications/decision_worker.py:34-104`, `decision_service.py:72-76`).
- Run-stop notices: a third debt definition, runs in paused/blocked/failed or in flight with a `pause_reason`, keyed
  by run revision, linking the PR URL (`pipeline_runs/repos.py:362-388`).
- Mapper hooks do not fire for Core bulk `update(PipelineRun)`; current bulk updates touch fields the projection does
  not read.

## Not verified

Migration-created indexes, visibility rules for projects, the backend predicate for replacement and dependency
acceptance, how an SDD batch leaves `attention`, whether a queued run records a catalog hold, and existing tests.
No EXPLAIN or live database check ran.
