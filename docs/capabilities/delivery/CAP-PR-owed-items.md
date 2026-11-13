---
id: CAP-PR-owed-items
title: Owed Items for Operator Debt
summary: "List and count every exception that waits for the operator across projects and object types, one item per root cause, through one read-only aggregate read with a fixed statement count and no provider call."
area: delivery
status: active
usecases:
  - UC-resolve-run-question
  - UC-deliver-pull-request
  - UC-execute-work-plan
  - UC-verify-project-connection
entrypoints:
  - modules/hub/app/features/project_management/owed_items/api.py
  - modules/hub/app/features/project_management/owed_items/usecases.py
  - modules/hub/app/features/project_management/owed_items/repos.py
---

# [CAP-PR-owed-items] Owed Items for Operator Debt

## 1. Summary

An owed item is one root cause that waits for the operator: a decision, a stopped PR run, a proposed Work Plan, a
Work Item recovery, replacement or attention, a connection-test cleanup review. Hub lists
and counts these items through one read surface, so every screen can count and route the same set. The operator-facing
label is "Needs you".

## 2. Scope & Boundary

- **In-Scope**: the owed-item model, its kinds and waiting predicates, root-cause suppression, the list and counts
  reads, and the per-run pending-decision flag on PR run reads.
- **Out-of-Scope**: each owner keeps its lifecycle and actions: decisions in `CAP-PR-operator-decisions` and
  `CAP-SDD-workflow-control`, PR runs in `CAP-PR-pull-request-delivery`, Work Plans in `CAP-WORK-work-plan-execution`,
  retired native history in `CAP-SDD-native-delivery`, connection tests in `CAP-CONN-connection-verification` and catalog holds
  in `CAP-AGENT-catalog-admission`. Notices stay in `CAP-NOTIFY-operator-notifications`.
- **Scope Excluded**: grouping owed items into threads or workspaces, owed-item notices, MCP exposure, a persisted
  owed projection and any action on the owed item itself. The app shell Badge reads the counts and the Attention
  landing reads the list (`UX-app-shell`, `UX-attention`).

## 3. Business Rules & Policies

1. **Kinds and weight**: Hub MUST classify each owed item as one of the kinds in §4 and MUST mark only `failed-run`
   as quiet (`counted` false). Check: [`test_owed_items.py`](../../../modules/hub/tests/integration/features/project_management/owed_items/test_owed_items.py), `test_every_kind_has_one_item_with_stable_shape`.
2. **Stable key**: Hub MUST key each item as `<kind>:<subject id>`, the `decision` kind embedding the unchanged
   `decision_key`, and MUST keep the key while the kind and subject stay the same. Check: the same test.
3. **One item per root cause**: WHEN several owners describe the same cause, Hub MUST list only the most specific:
   decision, then Work Item recovery or replacement, then Work Item `attention`, then run
   state. A run with any decision-inbox row is held by that decision. Check: `test_decisions_suppress_runs_and_match_the_inbox_count`,
   `test_failed_runs_are_quiet_and_recovery_wins`, `test_work_plan_and_work_item_kinds` and
   `test_batch_attention_suppresses_its_run_and_yields_to_decisions` and
   `test_a_batch_yielding_to_a_decision_hides_no_other_stopped_run` and
   `test_failed_runs_yield_to_batch_and_work_item_attention`.
4. **Decision parity**: WHEN counting, Hub MUST report a `decision` count equal to `actionable_total_count` of the
   decision list for the same `project_id` scope. Check: `test_decisions_suppress_runs_and_match_the_inbox_count`.
5. **Catalog holds are context**: Hub MUST never list an AI catalog as an item; WHEN a stopped run's catalog is held,
   Hub MUST report the hold in that item's `context.catalog_hold`. Check: `test_stopped_runs_carry_only_their_own_catalog_hold`.
6. **Bounded read**: WHEN listing or counting, Hub MUST use one database transaction on one connection with one
   aggregate statement, plus one project lookup when `project_id` is given, independent of row counts, and MUST make
   no provider call. Check: `test_one_transaction_and_fixed_statements_without_provider_calls`.
7. **Keyset pages**: WHEN listing, Hub MUST order by (`waiting_since`, `key`) with a limit-plus-one keyset cursor
   bound to the filters. Check: `test_keyset_pages_filters_and_errors`.
8. **Pending-decision flag**: WHEN Hub returns a PR run, it MUST set `has_pending_decision` to whether the run has an
   actionable decision-inbox row, loaded with the run row. Check:
   [`test_pending_decision_flag.py`](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_pending_decision_flag.py).

## 4. Interfaces & Data Contracts

### Kinds

| Kind | Counted | Waiting predicate (owner) | Subject type | Primary action |
| --- | --- | --- | --- | --- |
| `decision` | yes | Actionable decision-inbox row of a non-final run (`CAP-PR-operator-decisions`) | `decision` | `answer` |
| `stopped-run` | yes | `paused` or `blocked` PR run not held by a decision (`CAP-PR-pull-request-delivery`) | `pipeline-run` | `resume-run` |
| `work-plan-proposed` | yes | Work Plan in `proposed` (`CAP-WORK-work-plan-execution`) | `work-plan` | `review-plan` |
| `work-item-recovery` | yes | Recovery in `accepted` or `reconciling` (`CAP-WORK-work-plan-execution`) | `work-item-recovery` | `inspect-recovery` |
| `work-item-replacement` | yes | Active link whose original has a `waiting` dependent edge without a live acceptance (`CAP-WORK-work-plan-execution`) | `replacement-link` | `accept-replacement` |
| `work-item-attention` | yes | Work Item in `attention` (`CAP-WORK-work-plan-execution`) | `work-item` | `inspect-work-item` |
| `sdd-batch-attention` | legacy only | Retained native batch evidence; no new admission (`CAP-SDD-native-delivery`) | `sdd-batch` | `inspect-batch` |
| `connection-test-cleanup` | yes | Terminal test whose cleanup the operator can review (`CAP-CONN-connection-verification`) | `connection-test` | `review-cleanup` |
| `failed-run` | no | `failed` PR run (`CAP-PR-pull-request-delivery`) | `pipeline-run` | `inspect-run` |

`waiting_since` is the decision row's waiting time, the recovery's creation time, the connection test's finish time
(falling back to its `updated_at`) and otherwise the owner row's `updated_at`; Hub keeps no state-entry time.

### HTTP surface

Both reads are authenticated and follow the decision list's visibility: admitted users share projects.

| Method and path | Input | Result |
| --- | --- | --- |
| `GET /api/v1/owed-items` | `project_id`, `kind`, `cursor` (at most 4,096 characters), `limit` 1–100 (default 50) | `OwedItemPage`: `items`, `has_more`, `next_cursor` |
| `GET /api/v1/owed-items/counts` | `project_id` | `OwedItemCounts`: `total` (counted only), `by_kind` (every kind, zero included), `by_project` (counted, zero omitted) |

An item carries `key`, `kind`, `counted`, `cause`, `subject` (`type`, `id`, `project_id`, `title`), `primary_action`
(`name`, `label`), `waiting_since` and `context` (`run_id`, `work_plan_id`, `work_item_id`, `sdd_batch_id`,
`catalog_hold` with `catalog_id`, `reason` `unavailable` or `quota-blocked` and `available_at`). An unknown project
returns 404; an unknown kind, an out-of-range limit, a malformed cursor or a cursor with changed filters returns 422.

`PipelineRunRead.has_pending_decision` is a boolean on every PR run response.

### Read model

`ADR-owed-items-aggregate-read` records the decision: one read-only `OwedItemRepository` reads the owner models through
one `UNION ALL` branch per kind. It is the single place the owner predicates combine; an owner schema change updates
the branch and its test in the same change. The connection-test adapter check runs in the service and enters the SQL
predicate as the set of adapters with manual cleanup resolution.

## 5. Source and verification evidence

Source: [`owed_items/`](../../../modules/hub/app/features/project_management/owed_items) and the run flag in
[`pipeline_runs/models.py`](../../../modules/hub/app/features/project_management/pipeline_runs/models.py) and
[`discovery_projection.py`](../../../modules/hub/app/features/project_management/pipeline_runs/discovery_projection.py).
In `SPEC-owed-item-contract` the worker ran both test files above with `just test` (SQLite) and `just test-pg`
(PostgreSQL); the unit's review and final-report envelopes record the commands and counts. The tests use controlled
GitHub responses and do not establish live deployment behavior.
