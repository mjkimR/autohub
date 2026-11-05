---
id: CAP-CONN-connection-verification
title: Isolated Project Connection Verification
summary: "Connection tests verify a selected agent catalog against a project's real GitHub repository using isolated resources and current-head CI. Test outcomes remain separate from cleanup, and test pull requests cannot enter normal development or merge execution."
area: connections
status: active
usecases:
  - UC-verify-project-connection
entrypoints:
  - modules/hub/app/features/project_management/connection_tests/api.py
  - modules/hub/app/features/project_management/connection_tests/usecases.py
  - modules/hub/app/features/project_management/connection_tests/adapters/specs.py
---

# [CAP-CONN-connection-verification] Isolated Project Connection Verification

## 1. Summary

A connection test checks the provider's ability to produce a verifiable change
in the selected repository without merging it. A retained result identifies the
catalog, recipe and connection configuration checked, independently of whether
later remote cleanup has completed.

## 2. Scope & Boundary

- **In-Scope**: recipe readiness, idempotent test intake, pinned configuration,
  isolated GitHub resources, provider dispatch, marker/CI verification,
  cancellation/deadlines, safe cleanup and explicit cleanup reconciliation.
- **Out-of-Scope**: provider quota and capacity belong to
  `CAP-AGENT-catalog-admission`; normal PR implementation/merge belongs to pipeline
  execution; remote task cancellation remains a provider responsibility.
- **Scope Excluded**: merging a test PR, interpreting manual prerequisites as
  proven readiness, repeatedly creating an uncertain Jules session, or deleting
  unrelated PRs/branches merely because they descend from a test commit.

## 3. Business Rules & Policies

1. **Recipe readiness**: WHEN options are requested, Hub MUST report each registered recipe's prerequisites as `configured`, `missing` or `manual`, with readiness false if a required connector is missing. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_recipe_options_report_provider_specific_prerequisites`.
2. **Idempotent start**: WHEN a start request ID belongs to the same project without a conflicting explicit catalog, Hub MUST return the existing test rather than create another test. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_idempotent_start_and_uncertain_mention_reconcile`.
3. **Conflicting start**: IF another test is running for the project or the request ID belongs to another project/requested catalog, THEN Hub MUST refuse the start with HTTP 409 `CONFLICT`. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_idempotent_start_and_uncertain_mention_reconcile` and `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_catalog_identity_retries_and_admission_hold`.
4. **Configuration identity**: WHEN credentials rotate or the project configuration changes during a running test, Hub MUST request cancellation instead of dispatching against the changed configuration. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_configuration_fingerprint_ignores_quota_but_detects_credential_rotation` and `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_other_project_cannot_control_test_and_settings_change_stops_dispatch`.
5. **Shared admission**: WHILE a running test awaits dispatch and catalog admission is refused, Hub MUST retain the test at dispatching without creating a provider execution. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_catalog_identity_retries_and_admission_hold`.
6. **Creation reconciliation**: WHEN the response to a Jules create attempt is uncertain, Hub MUST reconcile that original attempt without issuing another create request. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_jules_unknown_create_is_reconciled_without_duplicate_sessions`.
7. **Verified head**: WHEN declaring a test succeeded, Hub MUST have observed the exact test marker on a changed PR head whose required CI passed for that same head. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_wrong_marker_and_skipped_ci_do_not_verify` and `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_success_never_merges_and_preserves_result_when_cleanup_retries`.
8. **No development enrollment**: WHEN a recognized test PR is submitted to normal development execution, Hub MUST refuse it with HTTP 422 `INVALID_REQUEST` even after test completion. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_probe_cannot_be_enrolled_even_after_completion` and `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_jules_output_is_blocked_before_scheduler_discovers_it`.
9. **No test merge**: WHEN final merge authorization encounters a test PR, Hub MUST refuse authorization rather than merge it. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_jules_test_cannot_bypass_final_merge_gate`.
10. **Terminal cancellation**: WHEN cancellation or the one-hour deadline is observed, Hub MUST preserve a terminal `canceled` or `timed_out` outcome despite later provider pushes. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_cancel_or_deadline_closes_pr_and_delays_branch_cleanup`.
11. **Independent cleanup result**: WHEN cleanup fails after verification succeeds, Hub MUST retain the successful verification outcome while reporting cleanup failure separately. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_success_never_merges_and_preserves_result_when_cleanup_retries`.
12. **Positive cleanup ownership**: IF a possible Jules output lacks positive ownership proof, THEN Hub MUST leave that PR unmodified and retain unresolved cleanup protection. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_default_branch_inheriting_test_commit_never_grants_cleanup_ownership` and `modules/hub/tests/integration/features/project_management/connection_tests/test_cleanup_safety.py::test_unmarked_wrong_base_output_is_quarantined_until_provider_confirms_it`.
13. **Delayed failed-test deletion**: WHILE a nonsuccessful test finished less than one day ago, Hub MUST defer branch deletion. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_cancel_or_deadline_closes_pr_and_delays_branch_cleanup`.
14. **Unresolved discovery**: WHILE provider output remains unconfirmed or the GitHub discovery scan is incomplete, Hub MUST retain protection beyond the one-day cleanup delay. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_cleanup_safety.py::test_incomplete_github_discovery_cannot_retire_protection` and `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_intent_without_post_can_be_resolved_without_creating_a_session`.
15. **Cleanup review freshness**: IF cleanup reconciliation has an active worker lease, changed candidate heads, a confirmed test PR dismissed as unrelated, or conflicting replay details, THEN Hub MUST refuse reconciliation with HTTP 409 `CONFLICT`. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_cleanup_resolution_rejects_active_leases_and_stale_candidate_heads` and `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_intent_without_post_can_be_resolved_without_creating_a_session`.
16. **Project isolation**: WHEN another project's endpoint requests control of a test, Hub MUST return HTTP 404 `NOT_FOUND`. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_other_project_cannot_control_test_and_settings_change_stops_dispatch`.

17. **Visible test metadata**: WHEN a PR carries a reserved test head/base, test marker or test label, Hub MUST reject normal enrollment even before its output ID is discovered. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_visible_test_metadata_blocks_enrollment_without_known_id`.
18. **Best-effort ownership marking**: WHEN an output has positive cleanup ownership, Hub MUST preserve that ownership independently of whether adding its visible marker or label succeeds. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_provider_owned_pr_gets_marker_and_label_even_when_agent_omits_them` and `modules/hub/tests/integration/features/project_management/connection_tests/test_ownership_recovery.py::test_label_permission_failure_does_not_prevent_owned_pr_cleanup`.
19. **Retained PR identity**: WHEN completed test history contains a known owned PR ID, Hub MUST keep that PR excluded without performing ancestry lookups for unrelated regular PRs on behalf of the completed history. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_completed_history_skips_ancestry_checks_but_keeps_all_owned_pr_ids`.
20. **Cleanup connector retention**: WHILE a running test or unfinished cleanup references its captured GitHub or catalog connector, Hub MUST refuse deletion of that connector after reassignment. Tests: `modules/hub/tests/integration/features/project_management/connection_tests/test_cleanup_safety.py::test_detached_github_connector_is_retained_until_cleanup_completes` and `modules/hub/tests/integration/features/project_management/connection_tests/test_cleanup_safety.py::test_replaced_catalog_connector_is_retained_for_provider_reconciliation`.
21. **Claim arbitration**: WHILE a worker holds a test's unexpired lease, Hub MUST prevent a second worker from advancing the same test step. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_worker_lease_prevents_duplicate_steps_and_preserves_concurrent_cancel`.
22. **Concurrent cancellation**: WHEN cancellation arrives during provider observation, Hub MUST preserve the cancellation instead of replacing it with the worker's running or successful snapshot. Test: `modules/hub/tests/integration/features/project_management/connection_tests/test_connection_tests.py::test_worker_lease_prevents_duplicate_steps_and_preserves_concurrent_cancel`.

## 4. Interfaces & Data Contracts

Base path: `/api/v1/projects/{project_id}/connection-tests`.

| Method and suffix | Contract |
| --- | --- |
| `GET` collection | Returns test records for the project |
| `GET /options` | Returns recipe, requirements, configuration fingerprint and `ready` per supported catalog |
| `POST` collection | `{request_id: UUID, ai_catalog_id?: UUID or null}`; HTTP 201 with the new or existing record |
| `POST /{test_id}/advance` | Advances one claimable test step and returns its record |
| `POST /{test_id}/cancel` | Requests cancellation, advances if claimable and returns its record |
| `POST /{test_id}/resolve-cleanup` | Records an operator's reviewed terminal-test cleanup resolution and advances cleanup |

A new test requires an enabled project, GitHub configuration and an enabled
catalog with supported recipe and configured connector prerequisites; refusal is
HTTP 422 `INVALID_REQUEST`. An omitted catalog uses the project's selected
catalog, falling back to `personal-codex`. Readiness is not quota availability:
manual requirements remain manual, and dispatch subsequently uses shared admission.

The record includes `id`, `project_id`, `project_revision`, `repository`,
`ai_catalog_id`, `catalog_snapshot`, `configuration_current`,
`cleanup_resolution_available`, `test_spec`, `status`, `phase`, `cleanup_status`,
`detail`, `evidence`, `cancel_requested`, `created_at`, `deadline`, `finished_at`.
Test status is `running`, `succeeded`, `failed`, `timed_out` or `canceled`;
cleanup status is independently `pending`, `waiting`, `completed` or `failed`.
Creation sets a one-hour deadline. A claimed external-I/O step has a 60-second
budget; transient observation errors can leave the test running for a later retry.
The repository claims a step with a 90-second lease and writes its outcome only
under the same lease token. Reads do not create PRs or comments. A legacy record
without a matching catalog fingerprint does not verify another selected catalog.

The fingerprint covers recipe identity, catalog identity/enabled state, project
repository/enabled state, verification settings and connector identity/configuration/
credential version. Catalog names, quota state and catalog revision alone do not
invalidate it. Only the digest is persisted/returned as the configuration identity.

The isolated branch is `autohub-connection-test/{test_id}` and the fixture is
`.autohub/connection-tests/{test_id}.txt`; verification requires exact UTF-8 content
`verified:{test_id}` followed by a newline. Codex receives a mention on an isolated
Draft PR; its first reply releases execution capacity and a missing push after a
five-minute observation grace fails the test. Jules creates one session from the
isolated branch and requires its output PR to remain in the same repository,
descend from the isolated commit and target the isolated base. Wrong-base or
multiple owned outputs fail verification and enter owned-output cleanup.

Cleanup closes owned PRs without merging. Successful tests may delete their
isolated branches immediately; other outcomes wait at least one day. Jules cleanup
also waits for confirmed output discovery and preserves default/base branches.
Provider unavailability does not prohibit GitHub cleanup of already proven outputs.

Positive ownership proofs are provider output, a verified per-test marker, or the
reserved Codex branch. Confirmed output is marked with
`<!-- autohub-connection-test:{test_id} -->` and label `autohub-connection-test`
when permissions allow; marking failures remain warnings. Ancestry alone permits
quarantine, not editing/closing/deleting a candidate. Known PR IDs remain protected
after cleanup and base changes. Only unresolved discovery adds ancestry checks to
regular enrollment; completed history does not. Source `protected_heads` limits
this unresolved lookup to 20 tests and returns HTTP 409 `CONFLICT` beyond that
bound instead of scanning without limit. The bound is source-inspected in
`modules/hub/app/features/project_management/connection_tests/repos.py`.
Hub's merge exclusion does not prevent external users or GitHub automation from
merging a test PR. Manual fixture pushes can satisfy the observed marker; this
check does not authenticate the push author as the requested agent.

Cleanup resolution accepts `request_id`, `confirmed_remote_stopped=true`, a trimmed
`note` (1–1000 characters), and `unrelated_pulls` mapping candidate PR numbers to
reviewed head SHAs (at most 1000 entries, default empty). It is available only for a
supported terminal recipe with unresolved discovery/candidates. Accepted resolution
records the review and requires another bounded GitHub scan; it never retries
provider creation. Replaying the same resolution returns the existing result;
changed replay details conflict. Request schema violations return HTTP 422.

## 5. Implementation and Verification Sources

Inspected source: `modules/hub/app/features/project_management/connection_tests/`
(`api.py`, `schemas.py`, `services.py`, `usecases.py`, `configuration.py`, `catalogs.py`,
`github.py`, `guards.py`, `recovery.py`, `adapters/codex.py`, `adapters/jules.py`,
`adapters/jules_cleanup.py`, `adapters/specs.py`) and shared catalog admission.
The existing tests cited above exercise the contract; this document does not
report their execution or a new live GitHub/provider check. Historical live scope
and manual-intervention limits remain in the
[production evidence](../../materials/2026-10/20261002-production-verification/report.md).
Operational details are in [provider connections](../../operations/provider-connections.md).
