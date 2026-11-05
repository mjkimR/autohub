---
id: CAP-WORK-work-plan-execution
title: Work Plan Execution
summary: "Auto Hub retains pre-PR work and admits dependency-ready Items under project and catalog capacity, then records confirmed merge outcomes. Revision-checked controls, registration identity and outbound Issue mirrors preserve execution ownership during retries and recovery."
area: work-plans
status: active
usecases:
  - UC-execute-work-plan
entrypoints:
  - modules/hub/app/features/project_management/work_plans/api.py
  - modules/hub/app/features/project_management/work_plans/services.py
  - modules/hub/app/features/project_management/work_plans/execution.py
---

# [CAP-WORK-work-plan-execution] Work Plan Execution

## 1. Summary

A `WorkPlan` holds local specifications, a Plan dependency graph and an Item
dependency graph before PRs exist. Admission prepares or explicitly attaches each
eligible Item's branch/PR and hands it to `CAP-PR-pull-request-delivery`.
`UC-execute-work-plan` describes the operator's path to confirmed completion.

## 2. Scope & Boundary

- **In-Scope**: seed/proposal/held/active registration, request replay, graph
  validation, revision-checked edits and controls, scheduled eligibility, capacity
  reservation, branch preparation/reconciliation, outcome retention, activity and
  outbound GitHub Issue mirrors.
- **Out-of-Scope**: PR implementation, CI fixes and merge authorization belong to
  `CAP-PR-pull-request-delivery`; GitHub owns actual PR merge facts; native SDD
  binding and SDK execution use separate paths.
- **Scope Excluded**: cross-Plan Item dependencies, automatic WBS/decomposition,
  bidirectional Issue synchronization, failed-Item retry APIs and automatic
  substitution of successor Plans. `group_key` is classification metadata, not an
  execution, permission or filesystem-isolation policy.

## 3. Business Rules & Policies

1. **Atomic graphs**: IF Item keys/edges are invalid or a dependency graph contains missing targets, cycles, self references or cross-Plan Item edges, THEN Hub MUST reject the write without retaining a partial graph. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_registration_is_atomic_and_cross_plan_item_dependencies_are_rejected` and `test_plan_cycles_rejected_and_revision_control`; [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_invalid_graph_rolls_back_and_ready_membership_stays_fixed`.
2. **Registration identity**: WHEN an existing project's registration request ID is replayed with equivalent normalized work, Hub MUST return the original Plan's current state. Check: [`test_registration.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_registration.py), `test_replay_recovers_original_even_after_plan_changes`.
3. **Changed registration**: IF an existing registration request ID is reused with different work, THEN Hub MUST return HTTP 409 instead of editing the original Plan. Check: [`test_registration.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_registration.py), `test_replay_recovers_original_even_after_plan_changes`.
4. **Explicit activation**: WHILE a Plan is `draft`, `proposed` or `paused`, Hub MUST admit no unstarted Item from it. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_nonactive_registration_never_admits`.
5. **Complete activation input**: WHEN a draft/proposed Plan is proposed, made ready or resumed, Hub MUST require at least one Item with title, specification and acceptance. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_seed_requires_explicit_validated_transition_and_preserves_replay`.
6. **Review invalidation**: WHEN editable `proposed` work changes, Hub MUST return the Plan to `draft`. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_proposed_edit_returns_to_draft_and_membership_history_is_durable`.
7. **Scheduled lower bound**: WHERE `scheduled_at` is set, WHILE the current time precedes that instant, Hub MUST withhold Item admission even after create, edit, resume, webhook or tick processing. Check: [`test_scheduling.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_scheduling.py), `test_future_schedule_gates_create_edit_resume_and_tick_until_boundary` and `test_scheduled_plan_does_not_hold_capacity_and_webhook_cannot_start_it_early`.
8. **Capacity-aware admission**: WHEN admitting independent Items, Hub MUST reserve preparation and existing queued/active work against the shared project/catalog capacity before admitting more. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_independent_work_uses_shared_capacity_and_pause_fences_selected_work`; [`test_review_regressions.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_review_regressions.py), `test_each_run_reserves_one_slot`.
9. **Merge-based release**: WHEN evaluating an Item's dependency, Hub MUST require its predecessor's confirmed merge into the original repository/target branch rather than a missing Run or a merge into a different target. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_merge_releases_items_then_plans_from_latest_base` and `test_missing_run_and_wrong_target_never_release_dependencies`.
10. **Unstarted control boundary**: WHEN Plan pause or revoke wins before admission commits, Hub MUST prevent that waiting Item from starting. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_independent_work_uses_shared_capacity_and_pause_fences_selected_work`.
11. **Admitted work continues**: WHEN pause or revoke follows committed admission, Hub MUST preserve the admitted Item's execution and observed result. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_pause_revoke_and_resume_only_control_unstarted_items` and `test_claimed_preparation_continues_after_pause_and_stale_lease_cannot_write`.
12. **Terminal Plan control**: WHILE a Plan is `completed` or `revoked`, Hub MUST reject lifecycle controls with HTTP 409. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_pause_revoke_and_resume_only_control_unstarted_items`; the `completed` branch is also explicit in `WorkPlanService.control`.
13. **PR response-loss recovery**: IF PR creation succeeded but its response was lost, THEN Hub MUST reconcile that Item's existing branch/PR before creating another PR. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_pr_creation_response_loss_reconciles_without_duplicate`.
14. **Foreign activity branch**: IF the default activity branch already carries work that is not this Item's earlier preparation, THEN Hub MUST stop preparation in `preparation_failed` without overwriting it. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_new_start_is_refused_when_the_activity_branch_already_exists`.
15. **Explicit attach**: WHERE `attach_branch` identifies an existing remote activity branch, Hub MUST use that branch's existing open PR or prepare a new PR from the same branch when none is open, without creating a replacement branch. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_explicit_attach_reuses_the_branch_and_adopts_its_open_pull_request` and `test_explicit_attach_needs_the_branch_on_the_remote_and_an_activity_name`.
16. **Preparation failure boundary**: IF a readable exact-ref lookup confirms the base branch is absent before preparation writes, THEN Hub MUST retain `preparation_failed` and release its admission capacity. Check: [`test_review_regressions.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_review_regressions.py), `test_bad_base_releases_capacity_and_preserves_failure`.
17. **Uncertain preparation**: IF external preparation has an unconfirmed or transient outcome, THEN Hub MUST retain its preparation identity/reservation for reconciliation instead of restarting it as new work. Check: [`test_review_regressions.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_review_regressions.py), `test_transient_preparation_failure_keeps_identity_and_reservation`; [`test_preparation_recovery.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_preparation_recovery.py), `test_private_ref_404_without_readable_listing_remains_retryable`.
18. **Independent Issue mirrors**: WHEN Issue publication fails or a remote Issue is edited/closed, Hub MUST keep execution and dependency decisions based on local specifications and confirmed PR outcomes. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_issue_failure_does_not_gate_execution_and_lost_response_reconciles`.
19. **Durable success before pruning**: WHEN detailed Run history becomes eligible for deletion, Hub MUST preserve Item success and merge evidence before retiring its Run link. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_retention_requires_durable_success_and_preserves_failed_work`.
20. **Comments are context**: WHEN a Plan comment is accepted or identically replayed, Hub MUST leave execution eligibility and Plan revision unchanged. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_comments_are_idempotent_context_only_and_activity_is_paged`.
21. **Classification is metadata**: WHEN `group_key` changes under its revision check, Hub MUST leave Plan lifecycle and Item execution unchanged. Check: [`test_groups.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_groups.py), `test_reclassification_preserves_registration_and_never_kicks_work` and `test_group_changes_preserve_lifecycle_state`.
22. **Exact group selection**: WHEN a group filter is supplied, Hub MUST apply its normalized exact project-local match before pagination and totals. Check: [`test_groups.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_groups.py), `test_filters_are_exact_paginated_and_project_scoped`.
23. **Transactional activity**: IF saving a Plan mutation's activity fails, THEN Hub MUST roll back that specification mutation. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_audit_failure_rolls_back_plan_edit`.
24. **Accepted unchanged mutation**: WHEN an accepted update or control changes no specification value, Hub MUST still record its accepted revision, reason and authenticated actor. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_unchanged_mutations_record_accepted_revision_and_reason`.
25. **Protect unresolved execution**: WHILE an attached Item lacks eligible successful merge evidence, Hub MUST preserve its linked Run from age-based pruning even if the Run failed. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_retention_requires_durable_success_and_preserves_failed_work`.
26. **Unpublished seeds**: WHILE a Plan remains draft/proposed or is revoked before any mirror exists, Hub MUST create no Issue mirror for it. Check: [`test_backlog.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_backlog.py), `test_draft_filter_withdrawal_and_revocation_do_not_publish`.
27. **Draft key integrity**: WHEN editable task keys are renamed or swapped in the Plan form, the UI MUST preserve their intended dependency relationships instead of submitting an intermediate invalid key set. Check: [`WorkPlansPanel.integration.test.ts`](../../../modules/hub-ui/src/lib/features/project-management/work-plans/WorkPlansPanel.integration.test.ts), `renames %s task keys and preserves dependent references`, `swaps task keys without redirecting their dependency relationships` and `retains an invalid key and blocks saving after other tasks are removed or added`.
28. **Replacement does not release old dependencies**: WHEN a replacement Plan completes, Hub MUST leave the original failed/revoked Plan's dependent work unreleased unless its original dependency conditions are independently satisfied. Check: [`test_registration.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_registration.py), `test_replacement_keeps_canceled_evidence_and_does_not_release_old_dependents`.

## 4. Interfaces & Data Contracts

### HTTP surface

Base: `/api/v1/projects/{project_id}/work-plans`; all routes use the project's
application access boundary. The operation's observed revision is required for
edits, controls and group changes.

| Method and suffix | Contract |
| --- | --- |
| `POST` base | HTTP 201; register `title`, optional `request_id`, state, Plan dependencies and Items |
| `GET` base | `offset`, `limit` 1–100, optional lifecycle/group filters; `items` and `total_count` |
| `GET /{plan_id}` | Current Plan, Items, dependency keys, result and mirror status |
| `GET /registrations/{request_id}` | Recover the registration in this project without creating work |
| `PUT /{plan_id}` | Replace editable specification/graphs with `expected_revision` and optional reason |
| `POST /{plan_id}/control` | `action`, `expected_revision`, optional reason |
| `PATCH /{plan_id}/group` | `group_key`, `expected_revision`, optional reason; no execution kick |
| `GET /{plan_id}/activity` | Paged history and optional `comments_only` filter |
| `POST /{plan_id}/comments` | HTTP 201; `request_id`, plain `body` of 1–8,000 characters |

`WorkPlanCreate.state` defaults to `active`. Only `draft` accepts zero Items or
incomplete Item text. Other initial states require 1–100 complete Items. Each
Item has `key`, `title`, `description`, `acceptance`, local `depends_on` keys and
optional `attach_branch`. Keys match `[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}`. Plans carry
`base_branch` (default `main`), optional timezone-aware `scheduled_at` normalized
to UTC, and Plan dependencies from the same project. Unknown input fields and
agent-trigger mentions in Item text are rejected by the schemas.

### Lifecycle and ownership

| State | Admission and allowed control actions |
| --- | --- |
| `draft` | No admission; `propose`, `ready`, `resume`, `revoke` |
| `proposed` | No admission; `draft`, `ready`, `resume`, `revoke` |
| `paused` | No new admission; `pause`, `resume`, `revoke` |
| `active` | Due dependency/capacity checks apply; `pause`, `resume`, `revoke` |
| `completed`, `revoked` | No lifecycle controls |

`ready` holds validated work in `paused`; `resume` requests execution in `active`.
Plan and Item graphs must both be acyclic. Plan dependencies wait for
`completed`; Item dependencies wait for `succeeded`. A paused Plan can complete
when all already-started Items succeed; a revoked Plan does not become completed.
Text/dependency edits require no Item to have started. Draft/proposed membership
is flexible; active/paused membership keys are fixed. Stale revisions return 409;
invalid graphs or incomplete activation return 422; absent Plan/request IDs
return 404. No new stable error code is introduced here.

Admission commits `preparing`, `started_at`, catalog, branch and a lease before
remote preparation. Default branches are `dev-<lowercased-key>`; explicit attach
accepts a remote `plan-*` or `dev-*` branch matching the shared activity-branch
rule. Recoverable ownership evidence includes this Item's marked PR, preparation
file or untouched tip at its recorded base. Fresh PRs are created ready for
review with the local specification, and their Runs use the shared PR executor.
Human Draft changes and project merge policy remain effective.

Item outcomes include `waiting`, `preparing`, `running`, `succeeded`,
`preparation_failed`, `attention` and projected Run attention/stop states.
Missing execution or changed PR identity/target produces `attention`, not success.
Source handling for a native `sdd` project also stops an Item in `attention`
because native execution needs a bound spec; Work Plans do not create that binding.

`request_id` deduplicates only when supplied. Its normalized work digest ignores
classification and ordering of Item/dependency arrays; it does not detect
semantic duplicates under different IDs. Active create/edit/resume calls perform
a bounded immediate kick after committing; unfinished work stays due for ticks.
`scheduled_at` is an earliest time, not an exact-time execution guarantee.

Replacement work is another registration with a new `request_id`, descriptive
links to the original work and, when reusing its branch, `attach_branch`. There
are no `replaces_*` fields or successor-substitution API. Completion belongs to
the replacement graph; independently enrolling a PR does not satisfy the
original Item's dependency because its recorded execution/merge evidence is
still evaluated separately. Registration identity remains on its Plan row for
the lifetime of that Plan.

### Classification and activity

`group_key` is case-sensitive, at most 100 characters and trimmed; empty values
normalize to null. Omitted/null list filters select all groups, an empty-string
filter selects ungrouped work and a nonempty filter selects an exact normalized
key. Filtering combines with project/state before counts and pagination. Runs
inherit the current classification through their Item's Plan; no key is copied
into Run/request snapshots. Directly enrolled Runs are ungrouped. An omitted key
on ordinary edit preserves it; explicit null clears it. Reclassification can
occur in terminal Plan states and does not withdraw a proposal.

Activity rows include kind, authenticated actor, revision, time, reason/body and
field-level before/after changes. Creation, accepted updates/controls and automatic
completion record their activity transactionally; completed history uses the
system actor. Existing historical changes are not reconstructed. Unchanged
accepted updates/controls can have `changes: {}`; stale rejected writes and
registration replays add no change event. Group updates add an event when the
normalized classification actually changes.

Comments are append-only context, idempotent per Plan/request ID and actor/body.
Changed text or actor under the same comment ID conflicts. They do not increment
Plan revision, answer Run questions or authorize execution. Activity/comment
records follow Plan lifetime rather than detailed Run retention. There is no
comment edit/delete/thread, automatic rollback or GitHub comment synchronization.

### Outbound mirrors and retained results

Ready/active work publishes a Plan Issue and Item sub-issues. Desired snapshots
contain local specification, acceptance, dependency body links and PR/merge
identities; native GitHub blocking relationships are not synchronized. Bodies
retain at most 100 observed state transitions. Local changes can overwrite remote
Issue edits; remote Issue contents are never execution input.

Issue publication has separate pending/error state. A pass attempts at most four
records sequentially with a one-second gap, a 90-second lease and a five-minute
cooldown unless GitHub specifies a retry delay. Prompt webhook publication uses
a 20-second budget. A missing Plan Issue is published before Item links.
The connector needs Issues write access in addition to PR/Contents permissions;
missing Issues permission does not block PR execution.

Creation intent precedes posting. Reconciliation scans at most 1,000 Issues for
the entity marker and connector-author identity. Uncertain creation plus failed
or exhausted lookup remains pending without another POST. Only a definitive
creation refusal permits a fresh creation request. There is no manual resolution
API for an ambiguous missing Issue; connector-identity changes or deleted Issues
can require investigation without changing Item success.

Plan/Item specifications, edges and final results have no automatic expiry.
Successful Items retain repository/target, PR URL, merge SHA, execution identity
and completion time after detailed Run removal. An attached Run is eligible only
when its own last update and the Item's confirmed successful completion are each
older than 30 days, no active lease remains and explicit merge evidence exists.
Pruning nulls the link and records `pipeline_run_retired_at`; unresolved failed,
paused, blocked or missing-success work stays protected, including after Plan
revoke. Pruning and completion use compatible Run-before-Item locking.

Operator registration, group-conflict recovery and replacement-work procedures
belong in operational guides; schema and transition guarantees remain here.

## 5. Source and verification evidence

Source inspected: [`schemas.py`](../../../modules/hub/app/features/project_management/work_plans/schemas.py),
[`api.py`](../../../modules/hub/app/features/project_management/work_plans/api.py),
[`services.py`](../../../modules/hub/app/features/project_management/work_plans/services.py),
[`usecases.py`](../../../modules/hub/app/features/project_management/work_plans/usecases.py),
[`execution_repo.py`](../../../modules/hub/app/features/project_management/work_plans/execution_repo.py),
[`execution.py`](../../../modules/hub/app/features/project_management/work_plans/execution.py),
[`github.py`](../../../modules/hub/app/features/project_management/work_plans/github.py),
[`grouping.py`](../../../modules/hub/app/features/project_management/work_plans/grouping.py),
[`activity.py`](../../../modules/hub/app/features/project_management/work_plans/activity.py),
[`mirror_records.py`](../../../modules/hub/app/features/project_management/work_plans/mirror_records.py),
[`issue_sync.py`](../../../modules/hub/app/features/project_management/work_plans/issue_sync.py),
[`history.py`](../../../modules/hub/app/features/execution/tasks/domains/maintenance/history.py),
[`kick.py`](../../../modules/hub/app/features/project_management/work_plans/kick.py)
and [`activity_schemas.py`](../../../modules/hub/app/features/project_management/work_plans/activity_schemas.py).

The named tests were read, not executed for this contract. The integration
fixtures provide controlled GitHub/provider behavior; concurrency cases require
PostgreSQL and skip on SQLite. The native-project `attention` branch and some
individual schema limits above are source-inspected boundaries, not claims of
separately executed acceptance coverage. This contract does not establish live
GitHub execution, current deployment or Auto Hub's own SDD baseline.
