---
id: CAP-AGENT-catalog-admission
title: Agent Catalog Configuration and Admission
summary: "AI catalogs define provider adapters, operator controls, concurrency and quota admission shared by pipeline deliveries, agent sessions and connection tests. Provider execution and pull request merge authorization remain outside catalog admission."
area: agents
status: active
usecases:
  - UC-configure-agent-catalog
entrypoints:
  - modules/hub/app/features/ai_catalogs/api/v1.py
  - modules/hub/app/features/ai_catalogs/services.py
---

# [CAP-AGENT-catalog-admission] Agent Catalog Configuration and Admission

## 1. Summary

An AI catalog is the admission boundary for one named Codex or Jules execution
configuration. Configuration describes capacity and quota policy; admission reserves a
unit of work without granting permission to merge its eventual pull request.

## 2. Scope & Boundary

- **In-Scope**: catalog creation, provider connector assignment, enabled/availability
  controls, configured/effective concurrency, quota policy and dispatch accounting.
- **Out-of-Scope**: credentials and encryption belong to connector management;
  provider task/report execution belongs to the agent-session implementation;
  PR implementation and merge decisions belong to pipeline execution;
  isolated repository verification belongs to `CAP-CONN-connection-verification`.
- **Scope Excluded**: dynamic provider selection, shared-provider quota discovery,
  a catalog deletion API and inference that a saved catalog has working credentials.

## 3. Business Rules & Policies

1. **Provider adapter**: WHEN a valid catalog is created, Hub MUST assign `codex-github-mention` for `codex` or `jules-api` for `jules` rather than accept a caller-selected adapter. Test: `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_create_codex_defaults_list_and_disable` and `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_create_jules_with_connector_and_custom_quota`.
2. **Unique key**: IF a creation key already exists, THEN Hub MUST reject creation with HTTP 409 without replacing the existing catalog. Test: `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_duplicate_key_does_not_replace_existing_catalog`.
3. **Atomic validation**: IF creation fields or kind-specific policy settings are invalid, THEN Hub MUST reject the request with HTTP 422 without creating a catalog. Test: `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_invalid_creation_is_atomic`.
4. **Creation connector**: WHERE a connector is supplied at creation, Hub MUST accept only an existing enabled Jules connector for a Jules catalog. Test: `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_jules_rejects_wrong_disabled_or_missing_connector`.
5. **Credential-independent registration**: WHEN a Jules catalog has valid quota settings but no connector, Hub MUST permit catalog creation without claiming provider readiness. Test: `modules/hub/tests/integration/features/ai_catalogs/test_create_catalog.py::test_jules_can_be_created_before_credentials_are_registered`.
6. **Connector reassignment**: WHEN changing a catalog connector, Hub MUST accept only a Jules catalog with either no connector or an existing connector whose provider is `jules`. Test: `modules/hub/tests/integration/features/ai_catalogs/test_ai_catalogs_api.py::TestAICatalogsAPI::test_set_connector_accepts_only_the_kinds_provider`.
7. **Manual hold**: WHEN setting an availability hold, Hub MUST reject a nonfuture `available_at` with HTTP 422. Test: `modules/hub/tests/integration/features/ai_catalogs/test_ai_catalogs_api.py::TestAICatalogsAPI::test_set_and_clear_availability`.
8. **Hold preservation**: WHEN a disabled catalog with a retained availability time is enabled again, Hub MUST retain that hold for policy recovery rather than discard it. Test: `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_disabled_catalog_keeps_its_hold_through_re_enabling`.
9. **Concurrency control**: WHEN configured concurrency changes, Hub MUST apply the new cap to admission without terminating already admitted work. Checks: `modules/hub/app/features/ai_catalogs/services.py::set_concurrency`; `modules/hub/tests/integration/features/ai_catalogs/test_ai_catalogs_api.py::TestAICatalogsAPI::test_set_concurrency` verifies the saved cap and Codex probe cap.
10. **Gateway refusal**: WHILE a catalog is disabled, unknown or quota-blocked without an elapsed refresh time, Hub MUST refuse new dispatch admission. Checks: `modules/hub/app/features/ai_catalogs/services.py::_dispatch_rejection`; `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_unexpired_hold_is_returned_as_a_rejection_without_consulting_the_policy`.
11. **Capacity refusal**: WHEN active work reaches effective concurrency, Hub MUST refuse another admission without reserving its dispatch key. Test: `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_only_admitted_work_enters_the_dispatch_ledger`.
12. **Quota accounting**: WHEN an admitted unit is retried with its existing dispatch key, Hub MUST retain its original ledger admission instead of counting another task. Checks: `modules/hub/app/features/ai_catalogs/repos.py::reserve_dispatch`; `modules/hub/tests/unit/features/ai_catalogs/policies/test_daily_quota.py::test_reaching_the_limit_holds_until_the_oldest_task_ages_out_of_the_rolling_window` verifies exclusion of the retry's key from quota counting.
13. **Codex recovery**: WHEN an elapsed Codex hold is reconsidered, Hub MUST limit recovery to one concurrent probe until its delivered probe window elapses without another quota event. Tests: `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_probe_window_starts_only_after_the_probe_is_delivered` and `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_each_hold_re_anchors_on_the_probe_through_short_then_long_cycles`.
14. **Daily quota**: WHEN Jules admission reaches its configured daily task limit, Hub MUST hold further work until the rolling or calendar window has room plus the catalog's refresh jitter. Tests: `modules/hub/tests/unit/features/ai_catalogs/policies/test_daily_quota.py::test_reaching_the_limit_holds_until_the_oldest_task_ages_out_of_the_rolling_window` and `modules/hub/tests/unit/features/ai_catalogs/policies/test_daily_quota.py::test_calendar_window_counts_from_local_midnight_and_resets_at_the_next_one`.
15. **Unsupported policy**: IF a stored catalog kind has no quota policy, THEN Hub MUST reject admission instead of treating it as unlimited capacity. Test: `modules/hub/tests/unit/features/ai_catalogs/policies/test_codex_window.py::test_catalog_kind_without_a_quota_policy_is_never_admitted`.

16. **Default backfill**: WHEN default-catalog migration `e3c4d5e6f7a8` runs, Hub MUST insert only absent default keys without replacing existing identities, connectors, policy, enabled state or history. Tests: `modules/hub/tests/integration/migrations/test_default_ai_catalogs.py::test_missing_catalogs_are_seeded_and_reapplication_preserves_them` and `modules/hub/tests/integration/migrations/test_default_ai_catalogs.py::test_existing_catalog_and_custom_account_are_untouched`.
17. **Ledger pruning**: WHEN any catalog reserves new work, Hub MUST prune ledger entries older than 30 days across all catalogs. Test: `modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py::test_admitting_work_prunes_expired_ledger_rows_of_every_catalog`.
18. **Unconfirmed diagnostic capacity**: WHILE an admitted nonsuccessful connection test lacks execution-finished evidence, Hub MUST count it toward capacity while running or until one day after its terminal finish. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_unknown_execution_capacity_expires_even_when_cleanup_keeps_failing`.
19. **Finished diagnostic capacity**: WHEN remote connection-test execution completion is confirmed, Hub MUST release its execution capacity independently of cleanup success. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_completed_jules_execution_releases_capacity_before_failed_cleanup`.

## 4. Interfaces & Data Contracts

All paths below are under `/api/v1/ai-catalogs`.

| Method and suffix | Contract |
| --- | --- |
| `POST` collection | Creates a catalog; HTTP 201 with `AICatalogRead` |
| `GET` collection | Returns `{items: AICatalogRead[]}` |
| `PUT /{catalog_key}/enabled` | `{enabled: bool}` |
| `PUT /{catalog_key}/concurrency` | `{configured_concurrency: int}` in 1–1000 |
| `PUT /{catalog_key}/policy-config` | `{policy_config: object}` validated by kind |
| `PUT /{catalog_key}/connector` | `{connector_id: UUID or null}`; reassignment checks provider/existence, while connection readiness separately checks enabled credentials |
| `PUT /{catalog_key}/availability` | Future `available_at`, optional `note` up to 500 characters, `source` of `manual` or `local-codex-cli` |
| `DELETE /{catalog_key}/availability` | Clears the hold; restores `normal` if enabled or `disabled` otherwise |
| `GET /{catalog_key}/sessions` | `offset >= 0`, `limit` 1–100, optional `status` of `open`/`completed`/`failed` and `schedule_config_id`; returns `items` and `total_count` |

Creation fields are `key` (1–100 characters, `^[a-z][a-z0-9_-]*$`), `name`
(1–255 characters), `kind` (`codex`/`jules`), optional `connector_id`,
`configured_concurrency` (default 1), `policy_config` and `enabled` (default true).
Creation forbids extra fields and strips surrounding string whitespace.
Codex uses each project's GitHub connection and cannot receive a catalog connector.

The migration seeds `personal-codex` (`codex-github-mention`, concurrency 1) and
`personal-jules` (`jules-api`, concurrency 15, rolling daily task limit 100), both
enabled without a catalog connector. These are initial local policy values, not
automatically discovered provider entitlements. Existing keys remain unchanged;
the backfill's downgrade does not delete records that may own live references.

Codex policy defaults: `short_refresh_enabled=true`,
`short_refresh_cycle_minutes=300` (1–43200),
`long_refresh_cycle_minutes=10080` (1–525600),
`probe_window_minutes=10` (1–1440). Quota observations use up to two short-cycle
holds before a long-cycle hold; disabling short refresh selects the long cycle
immediately. A known current usage-window start anchors refresh; otherwise the
observation time does. Old observations do not move a verified hold earlier.

Jules requires `daily_task_limit` (1–10000); `window` defaults to `rolling`
(last 24 hours), with optional `calendar` and a valid IANA `timezone` (default
`UTC`). The daily ledger excludes the retried dispatch key. Provider quota refusals
outside the ledger produce a conservative full-window hold for rolling quotas.
Both policies add `refresh_jitter_minutes` (stored default 10) to refresh times.

`AICatalogRead` exposes identity, adapter, connector ID, enabled/availability
state, refresh time/source/note, configured/effective concurrency, policy
configuration/state, revision, held-run/active-dispatch/open-session counts and
supported pipeline/session/connection-test capabilities. Availability states are
`normal`, `quota_blocked`, `probe`, `disabled`, `unknown`.
Active capacity counts implementing/admitted pipeline work, open provider sessions
and admitted unfinished connection tests; merely waiting dispatches hold no slot.

Domain errors use HTTP 404 `NOT_FOUND`, 409 `CONFLICT` or 422 `INVALID_REQUEST`.
Schema-validation HTTP 422 is separate from `ProjectError` and is not assigned a
new domain code here. Internal admission returns `Admission(catalog, rejection)`;
a refusal can retain a quota-policy transition without reserving work. Missing
catalogs and invalid/unsupported policy state can still raise `ProjectError`;
returning an admission rejection is not a guarantee that this internal method
never raises. Catalog holds gate dispatch admission; current-head CI, pushes,
merge checks and quota-reply observation continue through their own run workflow.
The latter boundary is exercised by
`modules/hub/tests/integration/features/project_management/pipeline_runs/test_pipeline_runs_api.py::test_catalog_hold_gates_only_dispatching_runs`.

## 5. Implementation and Verification Sources

The contract is derived from `modules/hub/app/features/ai_catalogs/{api/v1.py,schemas.py,models.py,services.py,repos.py}`
and `policies/{registry.py,codex_window.py,daily_quota.py}`, together with the tests
cited above. The cited tests are existing verification coverage; this document
reports source/test inspection, not a new execution or live provider quota test.
Detailed operator procedures are in [provider connections](../../operations/provider-connections.md).

## Owed items

An AI catalog hold is a system hold that clears by itself, so it is never an owed item in `CAP-PR-owed-items`. A
stopped run on a held catalog reports the hold in its owed item's `context.catalog_hold`.
