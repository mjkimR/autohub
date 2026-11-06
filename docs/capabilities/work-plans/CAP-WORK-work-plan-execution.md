---
id: CAP-WORK-work-plan-execution
title: Work Plan Execution
summary: "Work Plans retain merge-confirmed outcomes and exact recovery identities. Project-owned revisioned templates create explicitly reviewed fresh Plans without copying execution authority."
area: work-plans
status: active
usecases:
  - UC-execute-work-plan
  - UC-reuse-work-plan-templates
  - UC-deliver-pull-request
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
`UC-execute-work-plan` describes the operator's path to confirmed completion. `UC-reuse-work-plan-templates` covers reusable definitions and fresh registration.

## 2. Scope & Boundary

- **In-Scope**: seed/proposal/held/active registration, request replay, graph
  validation, revision-checked edits and controls, scheduled eligibility, capacity
  reservation, branch preparation/reconciliation, explicit unchanged-work recovery, retained recovery history, outcome retention, explicit replacement evidence, activity and
  outbound GitHub Issue mirrors, reusable project-owned templates and atomic template registration provenance.
- **Out-of-Scope**: PR implementation, CI fixes and merge authorization belong to
  `CAP-PR-pull-request-delivery`; GitHub owns actual PR merge facts; native SDD
  binding and SDK execution use separate paths.
- **Scope Excluded**: cross-Plan Item dependencies, automatic WBS/decomposition,
  bidirectional Issue synchronization and automatic
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
9. **Merge-based release**: WHEN evaluating an Item's dependency, Hub MUST require the predecessor's confirmed original-target merge or a live exact-edge replacement acceptance under rules 37–43, rather than a missing Run or a different-target merge. Check: [`test_work_plans.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_work_plans.py), `test_merge_releases_items_then_plans_from_latest_base` and `test_missing_run_and_wrong_target_never_release_dependencies`.
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
28. **Descriptive replacement does not release**: WHEN an independently registered replacement Plan completes without explicit edge acceptance, Hub MUST leave the original failed/revoked Plan's dependent work held until its original dependency conditions are satisfied. Check: `test_replacement_keeps_canceled_evidence_and_does_not_release_old_dependents` in `test_registration.py`; the explicit exception is limited to local Item edges under rule 38. Whole-Plan dependencies still require completed predecessor Plans.

29. **Recovery identity**: WHEN an authenticated recovery request is identically replayed, Hub MUST return its original recovery record and current Item before rejecting stale revisions, without another acceptance event. Check: `test_preparation_recovery_replay_conflict_and_history` and `test_stale_and_cross_item_request_identity` in [`test_item_recovery.py`](../../../modules/hub/tests/integration/features/project_management/work_plans/test_item_recovery.py).
30. **Recovery history**: WHEN accepting recovery, Hub MUST retain an immutable command and prior Item/Run outcome snapshot with append-only ordered outcome events. Check: `test_preparation_recovery_replay_conflict_and_history`, `test_activity_failure_rolls_back_recovery_and_revision` and `test_history_survives_successful_run_pruning` in the recovery integration suite.
31. **Recovery fencing**: IF observed revisions, a live lease, Plan lifecycle, project mode or original PR identity prevent recovery, THEN Hub MUST refuse the stale or unsupported continuation without a fresh delivery. Check: `test_preflight_revision_and_live_leases_refuse_without_history`, `test_control_wins_after_remote_read_before_activation`, `test_review_project_mode_change_during_io_refuses_terminal_recovery` and `test_review_preparation_mode_change_while_held_refuses_before_admission`.
32. **Recovery ownership**: WHEN recovering failed work, Hub MUST retain the original Item and any linked Run rather than replace execution lineage. Check: `test_terminal_recovery_keeps_run_epoch_and_commits_delivery` and `test_three_item_chain_baseline_preserves_success_and_original_dependencies`.
33. **Recovery admission**: WHILE schedule, dependencies, enabled-project state, catalog availability or shared capacity holds recovery, Hub MUST preserve a visible awaiting-admission record without dispatch. Check: `test_recovery_uses_schedule_enabled_project_and_catalog_holds` and `test_capacity_hold_releases_without_reserving_or_losing_identity`.
34. **Recovery uncertainty**: WHILE the prior effect is uncertain, Hub MUST reconcile its original request identity before authorizing fresh work. Check: `test_uncertain_delivery_retains_identity_without_dispatch`. A definitive pre-write refusal closes that recovery; check: `test_definitive_recovery_preflight_refusal_closes_history_and_requires_new_request`.
35. **Recovery merge release**: WHEN recovery confirms the original-target merge of the last unfinished Item, Hub MUST complete its eligible Plan through ordinary completion and release dependent Plans. Check: `test_review_merge_completes_last_item_plan_and_releases_dependent_plan`.
36. **Retained specification fence**: WHILE failed preparation awaits recovery admission, Hub MUST retain the existing started-work fence against specification/target/dependency edits. Check: `test_review_held_preparation_preserves_edit_fence_before_and_after_refusal`.

37. **Replacement evidence**: WHEN recording replacement work, Hub MUST preserve original Item outcome, Plan lifecycle and PR ownership. Check: `test_exact_edge_release_consumption_and_replay` and `test_revoked_original_is_supported_without_reviving_plan` in `test_replacements.py`.
38. **Scoped satisfaction**: WHEN admitting a dependent using replacement evidence, Hub MUST satisfy only its explicitly accepted existing local Item edge while retaining every other admission gate. Check: `test_exact_edge_release_consumption_and_replay` and `test_accepted_edge_preserves_every_remaining_admission_gate`.
39. **Replacement lifecycle**: IF a relation changes a retained endpoint role, reuses a replacement or competes with a live original link, THEN Hub MUST refuse it with HTTP 409. Check: `test_retained_chain_and_reverse_roles_are_refused`, `test_unconsumed_withdraw_and_historical_endpoint_roles` and PostgreSQL competing-link barriers.
40. **Replacement consumption**: WHEN admission uses replacement acceptance, Hub MUST commit its immutable consumption event, evidence and original Plan revisions and activity with the admission. Check: PostgreSQL admission/withdrawal/control/recovery barrier tests in `test_replacements.py`.
41. **Consumed withdrawal**: IF an acceptance is consumed, THEN Hub MUST refuse withdrawal of that acceptance or its link with HTTP 409. Check: `test_exact_edge_release_consumption_and_replay` and PostgreSQL withdrawal/admission barriers.
42. **Exact replacement identity**: WHEN accepting an edge, Hub MUST bind the displayed specification digests and the replacement's own retained same-project/repository/connector/target confirmed merge evidence. Check: `test_acceptance_rejects_changed_review`, `test_real_binding_mismatches_refuse_without_changes` and `test_merge_snapshot_retains_after_pruning_and_other_holds`.
43. **Replacement request history**: WHEN the same project/operation request is identically replayed by the same authenticated actor, Hub MUST return its original result and current evidence before checking current revisions. Check: `test_replay_actor_path_and_withdrawn_receipt_identity`; changed actor, path or payload returns HTTP 409 without duplicate events.
44. **Linked specification fence**: WHILE an endpoint has a live replacement link, Hub MUST refuse specification/target edits or endpoint removal that would invalidate its reviewed identity. Check: `test_live_link_guards_edit_and_wrong_project_target`; started-work fences remain independent.
45. **Uncertain replacement review**: WHILE a replacement request outcome is unknown, the UI MUST retain its operation, endpoint and immutable command across Item remount/reload and permit exact replay rather than competing mutation. Check: `WorkItemReplacement.integration.test.ts`, including lost-response/authentication/remount and changed-basis regressions.

46. **Definition extraction**: WHEN an exact source Plan revision is saved as a template, Hub MUST extract only specification and local dependencies. Check: `test_source_extracts_only_definition_and_revision_guard` in `test_templates.py`.
47. **Independent definitions**: WHEN a template is saved, edited or deleted, Hub MUST leave derived Plan execution and retained provenance unchanged. Check: `test_template_crud_replay_and_deleted_receipt` and `test_registration_fresh_guards_replay_and_independence` in `test_templates.py`.
48. **Fresh preview identity**: WHEN a template preview is created, the UI MUST remap local keys/edges using stable source ordering, ordinal and a fresh request UUID. Check: `template-intent.integration.test.ts` under `modules/hub-ui/src/lib/features/project-management/work-plans/`.
49. **Current registration basis**: IF a fresh registration's template revision/digest or project repository/connector differs from its reviewed basis, THEN Hub MUST refuse before creating a Plan. Check: `test_stale_template_binding_refuses_without_plan` and PostgreSQL `test_registration_serializes_template_change` in `test_templates.py`.
50. **Atomic template provenance**: WHEN a template registration is accepted, Hub MUST commit its ordinary owner Plan and immutable original template/actor/request/binding/reviewed-payload receipt together. Check: `test_registration_receipt_failure_rolls_back_plan` in `test_templates.py`.
51. **Exact template replay**: WHEN an actor identically replays a project/operation/target/request/body, Hub MUST return its original recorded result before applying current eligibility checks. Check: `test_actor_and_target_bound_replay`, `test_strict_definition_path_actor_and_ordinary_collision` and the CRUD/registration replay tests in `test_templates.py`.
52. **Uncertain browser intent**: WHILE a template write result is unknown, the UI MUST retain its immutable original account/project session intent and block competing template writes across close/remount/reload. Check: `template-intent.integration.test.ts` and `WorkPlanTemplates.integration.test.ts`.
53. **Acknowledged browser result**: WHEN a template write is recorded or authoritatively refused, the UI MUST preserve that terminal result separately from later read/refresh failures across remount. Check: terminal recovery regressions in `template-intent.integration.test.ts`.
54. **Fresh review after refusal**: WHEN a reviewed template registration is refused, the UI MUST require explicit current-basis reload with a new request identity and confirmation before resubmission. Check: binding refusal regression in `WorkPlanTemplates.integration.test.ts`.
55. **Admission owner**: WHEN an explicitly active template registration commits, Hub MUST use the existing Work Plan owner admission path. Check: `test_post_commit_admission_failure_keeps_recorded_result` in `test_templates.py`; ordinary owner admission tests remain applicable.
56. **Private session cleanup**: WHEN the operator logs out, the UI MUST remove the template-intent session-storage namespace. Check: `modules/hub-ui/src/lib/stores/session.test.ts`.

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
| `POST /{plan_id}/items/{item_id}/recover` | Revision-checked explicit recovery; returns `recovery` and current `item` |
| `GET /{plan_id}/items/{item_id}/recoveries` | Paged immutable command/outcome history and ordered events |
| `GET /{plan_id}/activity` | Paged history and optional `comments_only` filter |
| `POST /{plan_id}/comments` | HTTP 201; `request_id`, plain `body` of 1–8,000 characters |

`WorkPlanCreate.state` defaults to `active`. Only `draft` accepts zero Items or
incomplete Item text. Other initial states require 1–100 complete Items. Each
Item has `key`, `title`, `description`, `acceptance`, local `depends_on` keys and
optional `attach_branch`. Keys match `[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}`. Plans carry
`base_branch` (default `main`), optional timezone-aware `scheduled_at` normalized
to UTC, and Plan dependencies from the same project. Unknown input fields and
agent-trigger mentions in Item text are rejected by the schemas.

### Reusable definitions and registration provenance

`UC-reuse-work-plan-templates` owns the operator goal. Base: `/api/v1/projects/{project_id}/work-plan-templates`; existing authenticated project access applies.

| Method and suffix | Contract |
| --- | --- |
| `GET` base | `offset`, `limit` 1–100; nondeleted definitions ordered by name/ID, `items`, `total_count` |
| `POST` base | New strict definition, name and request UUID; no execution |
| `POST /from-plan` | Source Plan ID and expected revision; allowlisted definition plus omissions |
| `GET /{template_id}` | Exact current template with revision and canonical digest |
| `PUT /{template_id}` | Full definition/name replacement with expected revision and request UUID |
| `DELETE /{template_id}` | Revision-aware soft deletion with request UUID |
| `POST /{template_id}/registrations` | Exact template revision/digest, expected repository/connector, request UUID and complete reviewed `WorkPlanCreate` payload |
| `GET /requests/{operation}/{request_id}` | Read-only original CRUD result or `record_state: unknown` |
| `GET /registrations/{request_id}` | Read-only original registration result or `record_state: unknown` |

Definitions retain schema version 1, project ownership, actor/time metadata and at most 100 local slots. They contain title/description/base branch and Item key/title/specification/acceptance/local dependencies. Attachments, Issue/PR/Run/history/approval, schedule/group and external Plan dependencies are omitted. The source branch is a candidate for fresh review.

Fresh preview keys use ASCII lexicographic source order, a stem of at most 22 characters, four-digit zero-based ordinal and full 32-digit request UUID hex. The preview defaults to draft with no group, schedule or external Plan dependency. The operator may explicitly edit all ordinary registration fields, including a fresh branch attachment. No attachment is copied from the template.

The wrapper locks Project then template and checks an existing receipt before current eligibility. A matching receipt recovers its original Plan even after template deletion or Plan changes. Reusing an ordinary registration ID without matching template provenance conflicts. Original snapshots and separately observed current template/Plan state remain distinguishable; no current definition reconstructs original authority. A postcommit mirror/admission refresh error preserves the recorded result.

`TEMPLATE_REVISION_CHANGED`, `TEMPLATE_SOURCE_CHANGED`, `TEMPLATE_BINDING_CHANGED`, `TEMPLATE_UNAVAILABLE` and `TEMPLATE_REFUSED` are authoritative refusals. Changed actor/path/body identity conflicts with HTTP 409. Authentication/access/transport failures and absent receipt reads leave a previously uncertain request unknown. The browser stores private immutable payload text in account/project-scoped `sessionStorage`; explicit exact retry is the only retrying write. Known outcomes survive remount until explicit dismissal or another reviewed operation. Logout or browser-session loss clears local recovery; only retained owner records can recover the old identity afterward. A new UUID does not deduplicate a lost intent.

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
return 404. Recovery error codes and local refusal reasons are described below.

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

### Explicit Work Item recovery

`ADR-work-item-recovery-lineage` records the retained Item/Run decision. Recovery accepts UUID `request_id`, `expected_revision >= 1`, `expected_run_revision >= 1` when linked and a trimmed `reason` of 1–500 characters. Hub derives the actor from the authenticated identity; recovery accepts no caller-supplied actor field. Project-local request uniqueness covers Item, actor and normalized command, including observed revisions. Changed content returns `RECOVERY_IDENTITY_CONFLICT` with HTTP 409. Access and Item scope are checked before replay; equivalent replay precedes stale-revision rejection (`RECOVERY_STALE`).

Local preflight accepts only an active Plan's `preparation_failed` Item without a Run or an Item linked to a `failed`/`canceled` Run. Successful/waiting Items, active/paused/blocked Runs, missing execution, live leases, changed bindings and native `sdd` projects are refused with a machine-readable reason and next action. Paused Plans require explicit resume. Remote reconciliation then verifies the same repository, branch, PR number and original target. A closed unmerged or foreign/wrong-target PR is refused; Hub never reopens it or substitutes another Run. Correctly merged original work records success without dispatch.

Acceptance atomically stores the command/snapshot, one Plan revision increment and authenticated activity. One pending recovery owns each Item. Events retain acceptance, reconciliation, admission, running, completion or refusal with ordered sequence numbers. History pages use `offset` and `limit` 1–100. Responses expose the current state/detail, `refusal_reason`, immutable prior repository/target/branch/head/execution evidence and actor/reason/time. Existing Items receive no invented historical recovery rows. Recovery history survives eligible detailed Run pruning.

Unknown remote reads and delivery outcomes remain reconciling, retaining original delivery markers. A definitive pre-write refusal closes the record and requires another explicit request after repair. Waiting for admission preserves historical `started_at`, so recovery cannot make started specifications editable. Admission rechecks the recovery identity, Plan revision and project mode. An expired or replaced worker lease cannot apply observations. The shared lock protocol is in `ARCH-06-execution`.

Terminal recovery delegates to the guarded owner in `CAP-PR-pull-request-delivery`. It retains epoch, attempt numbers, detailed delivery history and counters. Schedule/dependency/project/catalog/capacity gates still apply. A competing active owner closes the accepted record as refused with zero losing dispatch. The UI in `UX-work-plans` distinguishes accepted, awaiting-admission, reconciling, running and refused states and preserves a response-loss request through status lookup/replay.

### Explicit replacement evidence

The original Plan owns GET/POST `/{plan_id}/items/{item_id}/replacement-links`, POST `/{plan_id}/items/{item_id}/replacement-links/{link_id}/acceptances` and POST the same link's `/withdraw`, below `/api/v1/projects/{project_id}/work-plans`. Strict bodies reject unknown actor fields. Each command requires request ID, authenticated actor, reason, both Plan revisions and original Item evidence revision. Acceptance binds one existing dependent, both specification digests, merge SHA and execution identity. Withdraw names an optional acceptance ID; absence withdraws the whole unconsumed link.

Stopped originals are `preparation_failed`, `failed`, `canceled` or `revoked`, with no live Item/Run lease, pending recovery, nonterminal Run or retained success. Terminal original Plans remain inspectable and retain their holds. Linking can precede replacement success. Acceptance requires retained PR number/URL, branch, merge SHA, execution identity and completion time; detailed Run retirement preserves this evidence. These commands perform no provider I/O, PR mutation or dispatch. Operator review supplies semantic equivalence; Hub validates identity and merge facts.

An original has one active link. A replacement endpoint is bound for its retained lifetime, and endpoint roles never switch. Withdrawing an unconsumed link allows a distinct unused candidate. An unconsumed edge acceptance can be withdrawn and accepted again on the same live link. Consumed evidence is irreversible admission history. Original recovery success remains ordinary evidence; no original outcome becomes successful merely through replacement acceptance.

Responses distinguish the immutable command result from current relations, edge decisions and consumption history. GET keeps active relation/acceptance evidence available independently of historical pages. Inactive link history uses `offset` and `limit` (default 10, maximum 50). Event history uses `event_link_id` and `event_offset`, with 20 revision-ordered events per page; active/consumed acceptances and those referenced by the page accompany it. UI paging retains earlier historical context while applying current active/consumed flags.

Replacement mutation refusals preserve the existing `detail` error field and add feature-local codes. `REPLACEMENT_CONFLICT` (409) identifies an authoritative transaction refusal with current evidence revision; `REPLACEMENT_IDENTITY_CONFLICT` (409) identifies actor/path/payload conflict. Missing project-scoped objects return 404; malformed input returns 422. Authentication, inaccessible/unknown outcomes and identity conflicts do not prove the original unresolved operation failed. The UI preserves exact replay intent for those cases; an authoritative owner refusal requires refreshed explicit review. A successful write remains recorded if subsequent Plan refresh fails.

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

Template enforcement sources: `template_api.py`, `template_usecase.py`, `template_service.py` and `template_repo.py` in the Work Plan owner. API/rollback/replay/race tests are in `modules/hub/tests/integration/features/project_management/work_plans/test_templates.py`; the additive migration and historical metadata roundtrips are in `modules/hub/tests/integration/migrations/`. Actual local command evidence is retained in `SPEC-work-plan-templates`; these paths alone assert neither execution nor deployment.

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

Replacement implementation and checks are recorded in `SPEC-work-item-replacement`; source inspection and controlled test execution do not establish deployment. The original named tests were source-inspected. Executed recovery and affected-suite evidence is retained in `docs/materials/2026-11/20261105-work-item-retry/development-checks.md`; that evidence is distinct from live deployment. The integration
fixtures provide controlled GitHub/provider behavior; concurrency cases require
PostgreSQL and skip on SQLite. The native-project `attention` branch and some
individual schema limits above are source-inspected boundaries, not claims of
separately executed acceptance coverage. This contract does not establish live
GitHub execution, current deployment or Auto Hub's own SDD baseline.
