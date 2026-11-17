---
id: OPS-connection-test-outcomes
title: "Connection test stall, failure and cleanup routing"
status: active
summary: "Routes a connection test that is refused, stalls, fails or leaves cleanup unresolved to the catalog, provider-setup, CI or cleanup owner by its status, phase, detail and cleanup state; provider entitlements and remote task cancellation stay outside Hub evidence."
related_capabilities:
  - CAP-CONN-connection-verification
  - CAP-AGENT-catalog-admission
related_usecases:
  - UC-verify-project-connection
---

# [OPS-connection-test-outcomes] Connection test stall, failure and cleanup routing

An operator started a connection test for a project's selected AI catalog and it did not end `succeeded` with cleanup
`completed`. A ready recipe, a saved connector and a seeded catalog do not prove that the remote account can push, so
the cause can sit in Hub admission, the provider account, the provider's cloud environment, the repository's CI or
cleanup ownership. The test `status` alone does not separate them; `phase`, `detail`, `cleanup_status`,
`configuration_current` and the recorded evidence links do.

## Routing

The test record (UI **Connections** tab, REST `/api/v1/projects/{project_id}/connection-tests` or
`connection_tests_get`) carries `status`, `phase` (`preparing`, `dispatching`, `waiting_for_push`,
`waiting_for_session`, `verifying_ci`, `verified`), `detail`, `cleanup_status`, `configuration_current`,
`cleanup_resolution_available` and evidence such as the test PR, reply, session and CI links. The MCP view adds
`next_action`.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| No catalog to select, or a default catalog is missing | **Settings → AI Catalogs** lacks `personal-codex` or `personal-jules`; migration `e3c4d5e6f7a8` is not applied | [Prepare the project and catalog](../runbooks/provider-connections.md#prepare-the-project-and-catalog) step 1; `CAP-AGENT-catalog-admission` §3 rule 16 |
| Start refused as not ready | HTTP `422` `INVALID_REQUEST`; the options show `ready` false with a `missing` connector prerequisite, or the project, GitHub configuration or catalog is disabled | [Set up Jules](../runbooks/provider-connections.md#set-up-jules) steps 2–3 or [Prepare the project and catalog](../runbooks/provider-connections.md#prepare-the-project-and-catalog) step 2; `CAP-CONN-connection-verification` §4 |
| Start refused as a conflict | HTTP `409` `CONFLICT`; another test is `running` for the project, or the request ID belongs to another project or catalog | The existing record per [Verify the selected connection](../runbooks/provider-connections.md#verify-the-selected-connection) step 2; `CAP-CONN-connection-verification` §3 rule 3 |
| Test stays `running` at `dispatching` | `detail` carries the catalog admission rejection, and the catalog shows a hold, `disabled` availability or active work at its effective concurrency | [Adjust a Codex availability hold](../runbooks/provider-connections.md#adjust-a-codex-availability-hold) or the catalog's concurrency and quota in [Prepare the project and catalog](../runbooks/provider-connections.md#prepare-the-project-and-catalog) step 4; `CAP-AGENT-catalog-admission` §3 rules 10–11 and 14 |
| Test stays `running` with no new evidence | `detail` is unchanged across reads and no step advanced; nothing triggered the dispatcher | [Verify the selected connection](../runbooks/provider-connections.md#verify-the-selected-connection) step 3 |
| Jules test `running` at `waiting_for_session` | `detail` "Reconciling the original Jules create request; it will not be sent twice" | No action until reconciliation or the deadline; `CAP-CONN-connection-verification` §3 rule 6 |
| Codex test `failed` after a reply without a push | `detail` "Codex replied without pushing the test change; read its reply and check the environment GH_TOKEN"; evidence has `reply_url` and no `verified_sha` | [Set up Codex](../runbooks/provider-connections.md#set-up-codex) steps 2–3 |
| Codex test `failed` on a usage limit | `detail` "Codex reported its usage limit; the catalog will wait for quota recovery" | [Adjust a Codex availability hold](../runbooks/provider-connections.md#adjust-a-codex-availability-hold); `CAP-AGENT-catalog-admission` §3 rule 13 |
| Jules test `failed` before any GitHub resource | `detail` "Connect this repository in Jules before starting work" or another Jules API rejection; no test PR link | [Set up Jules](../runbooks/provider-connections.md#set-up-jules) step 1 |
| Jules test `failed` on the session or its output | `detail` starts "Jules session needs attention:" with the session state, or reads "Jules completed without a test PR in this repository", "Jules PR targeted a different base; closing the test PR" or "Jules returned multiple test PRs; closing all owned output" | The Jules session at its evidence link and [Set up Jules](../runbooks/provider-connections.md#set-up-jules); `CAP-CONN-connection-verification` §4 Jules output conditions |
| Test `running` at `waiting_for_push` or `waiting_for_session` with a changed head | `detail` "Head changed, but the requested test marker has not been verified" | The agent's change on the test PR; [Verify the selected connection](../runbooks/provider-connections.md#verify-the-selected-connection) step 4; `CAP-CONN-connection-verification` §3 rule 7 |
| Test at `verifying_ci` does not pass | Evidence has `verified_sha`; `ci_status` is skipped or missing (stays `running`) or `failed` (test `failed`); `detail` carries the CI reason | The repository workflow per [Set up Codex](../runbooks/provider-connections.md#set-up-codex) step 4 or [Set up Jules](../runbooks/provider-connections.md#set-up-jules) step 5 |
| Test `failed` because its PR changed outside Hub | `detail` "Test PR was closed before verification finished" or "Test PR branch no longer matches" | Rerun per [Verify the selected connection](../runbooks/provider-connections.md#verify-the-selected-connection); `CAP-CONN-connection-verification` §3 rule 7 |
| Test `timed_out` | `detail` "Verification timed out; check the provider's repository access, environment and test PR CI" after the one-hour deadline | The setup section for the catalog's provider, then a new test; `CAP-CONN-connection-verification` §3 rule 10 |
| Test `canceled` without an operator cancel | `configuration_current` false; a connector credential, catalog connector, catalog enabled state or project configuration changed while it ran | Rerun against the current configuration; `CAP-CONN-connection-verification` §3 rule 4 |
| Test `succeeded` but no longer applies | `configuration_current` false, `next_action` `review_configuration` | Rerun per [Verify the selected connection](../runbooks/provider-connections.md#verify-the-selected-connection) step 5 |
| Terminal test with `cleanup_status` `failed` | `next_action` `inspect_cleanup`; `detail` keeps the verification result | [Cancel or review cleanup](../runbooks/provider-connections.md#cancel-or-review-cleanup) first paragraph; `CAP-CONN-connection-verification` §3 rule 11 |
| Terminal test with `cleanup_status` `waiting` and no review offered | `cleanup_resolution_available` false; a nonsuccessful test finished less than one day ago | No action until the delay passes; `CAP-CONN-connection-verification` §3 rule 13 |
| Terminal Jules test with **Review cleanup** offered | `cleanup_resolution_available` true; output discovery is pending or a PR is unconfirmed, and the test is a `connection-test-cleanup` owed item | [Cancel or review cleanup](../runbooks/provider-connections.md#cancel-or-review-cleanup) second and third paragraphs; `CAP-CONN-connection-verification` §3 rules 12 and 14, §4 cleanup resolution |
| **Review cleanup** or connector deletion refused | Cleanup resolution returns HTTP `409` `CONFLICT` for an active worker lease, changed candidate heads or changed replay details; connector deletion is refused while unfinished cleanup references it | [Cancel or review cleanup](../runbooks/provider-connections.md#cancel-or-review-cleanup); `CAP-CONN-connection-verification` §3 rules 15 and 20 |

A test PR refused by normal enrollment with HTTP `422` `INVALID_REQUEST` is the intended exclusion of
`CAP-CONN-connection-verification` §3 rules 8 and 17, not a fault to route. For evidence that matches no row, read the
test's `detail` and evidence links and route to `CAP-CONN-connection-verification` §3 and §4.

## Normal-state observation

After the owner's action, a new test for the same project and catalog ends `status` `succeeded` at `phase`
`verified` with `verified_sha` and a passing `ci_status` for that head, `configuration_current` true and `next_action`
`done`, and its `cleanup_status` reaches `completed` separately. `CAP-CONN-connection-verification` owns these facts;
`CAP-AGENT-catalog-admission` owns the catalog's return to `normal` availability.

## Authority boundary

The provider account owns entitlements, cloud environment secrets and stopping an already dispatched remote task.
A verified marker does not authenticate who pushed it, and Hub's merge exclusion does not stop a person or external
GitHub automation from merging a test PR. A success applies only to the captured project and catalog configuration and
does not show available capacity for later work.

## Update triggers

- `CAP-CONN-connection-verification` §3 rules or §4 record fields, phases or cleanup contract change.
- `CAP-AGENT-catalog-admission` §3 rules 10–14 or 16 change.
- The `phase` or `detail` values in
  [github.py](../../modules/hub/app/features/project_management/connection_tests/github.py),
  [codex.py](../../modules/hub/app/features/project_management/connection_tests/adapters/codex.py),
  [jules.py](../../modules/hub/app/features/project_management/connection_tests/adapters/jules.py) or
  [services.py](../../modules/hub/app/features/project_management/connection_tests/services.py) change.
- The `next_action` precedence in [contracts.py](../../modules/hub/app/mcp/contracts.py) changes.
