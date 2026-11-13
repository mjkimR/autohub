---
id: CAP-SDK-task-flow-execution
title: Durable SDK Task and Flow Execution
summary: "The SDK declares versioned sequential task flows, while Auto Hub admits immutable releases and executes durable, authorized runs through configured workers. It excludes worker deployment; built-in SDD/PR bridge effects are retired."
area: sdk
status: active
usecases:
  - UC-execute-task-flow
entrypoints:
  - packages/sdk/src/autohub_sdk/flow.py
  - packages/sdk/src/autohub_sdk/client.py
  - modules/hub/app/features/execution/flows/api.py
---

# [CAP-SDK-task-flow-execution] Durable SDK Task and Flow Execution

## 1. Summary

`autohub-sdk` supplies declarations, wire models and an HTTP client independently
of the backend. Auto Hub owns release registration, run/attempt persistence,
maintenance-driven execution, approval and recovery. `CAP-SDK-existing-pr-bridge`
identifies the retired built-in SDD/PR binding and receipt-backed observation boundary.

## 2. Scope and Boundary

- **In-Scope**: manifest validation; release identity/activation; machine ownership;
  run admission and snapshots; sequential tasks and approvals; revisioned commands;
  worker dispatch, inspection and cancellation; input/output schema validation.
- **Out-of-Scope**: worker code deployment and external worker implementation belong
  to the operator/provider; local pipeline execution belongs to the SDK's local
  API; PR creation, CI and merging belong to the existing PR executor.
- **Scope Excluded**: parallel flow graphs, code upload, inferred field-level schema
  assignability, unconfigured native targets and automatic HTTP-client retries.

## 3. Business Rules and Policies

1. **Declared graph**: WHEN a manifest is validated, the SDK MUST reject duplicate task/flow contracts, duplicate step IDs, unknown task contracts, references to later tasks, a non-task result, and invalid approval revision targets. Check: `packages/sdk/tests/test_remote_contract.py`.
2. **Task bindings**: WHEN a release is validated, the SDK MUST require exactly one binding per declared task contract. Check: `packages/sdk/tests/test_remote_contract.py::test_release_catalog_and_bindings_are_consistent`.
3. **Machine boundary**: WHEN a release, run or command is accessed, the host MUST enforce the operation's machine scope and provider/environment ownership. Checks: `modules/hub/tests/integration/features/execution/flows/test_auth.py`, `modules/hub/tests/integration/features/execution/flows/test_host.py::test_owner_and_scope_isolation`.
4. **Release identity**: WHEN a registered release ID is reused, the host MUST return its receipt for equal content or refuse different content with `release-conflict`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_real_catalog_and_request_idempotency`.
5. **Activation revision**: WHEN activation is requested, the host MUST compare the environment's revision before changing its active release. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_real_catalog_and_request_idempotency`.
6. **Run identity**: WHEN a run idempotency key is reused within a provider/environment, the host MUST return the same run for equal request content or refuse different content with `request-conflict`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_real_catalog_and_request_idempotency`.
7. **Admission snapshot**: WHEN a new run is admitted, the host MUST retain the selected release's ID, digest, definition and resolved worker bindings for that run. Checks: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_real_catalog_and_request_idempotency`, `modules/hub/tests/integration/features/execution/flows/test_recovery.py::test_resolved_worker_binding_is_pinned_with_release`.
8. **Expected release**: IF a new request's expected release ID or digest differs from the active release, THEN the host MUST refuse admission with `release-mismatch` before creating a run. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_expected_release_rejects_activation_race_before_creating_run`.
9. **Command identity**: WHEN a command ID is reused for a run, the host MUST return the original receipt for equal content or refuse changed content with `command-conflict`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_approval_rework_and_command_receipt`.
10. **Revision fence**: IF a new command's expected revision differs from the run revision, THEN the host MUST refuse it with `stale-revision`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_worker_lease_and_concurrent_commands_postgres`.
11. **Approval authority**: WHEN approval or revision is commanded, the host MUST require `autohub:task:approve` in addition to write scope. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_owner_and_scope_isolation`.
12. **Cumulative attempts**: WHEN revision or explicit resume revisits a task, the host MUST preserve its consumed attempt count against `max_attempts`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_explicit_resume_cannot_reset_attempt_budget`.
13. **Approval deadline**: IF an approval deadline has elapsed, THEN the host MUST refuse an approval command with `approval-expired`. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_deadline_and_schema_errors`.
14. **Durable dispatch**: WHEN a worker operation is planned, the host MUST persist its attempt intent before external worker I/O. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_crash_after_effect_recovers_same_attempt`.
15. **Uncertain delivery**: WHEN an existing attempt has an unknown outcome, the host MUST inspect that attempt before resubmitting it under the same attempt ID after authoritative absence. Checks: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_authoritative_absence_resubmits_same_intent`, `modules/hub/tests/integration/features/execution/flows/test_recovery.py::test_unstructured_404_does_not_authorize_redispatch`.
16. **Late result fence**: IF the worker lease expires or its run revision changes during I/O, THEN the host MUST discard that worker's late result. Checks: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_cancel_and_inflight_revision_fence`, `modules/hub/tests/integration/features/execution/flows/test_host.py::test_expired_lease_reclamation_rejects_old_worker_result`.
17. **Output validation**: IF a completed task's output fails its declared schema, THEN the host MUST fail the task with `worker-output-invalid` before downstream execution. Check: `modules/hub/tests/integration/features/execution/flows/test_host.py::test_worker_output_schema_blocks_downstream_tasks`.
18. **Cancellation confirmation**: WHILE an external attempt is outstanding after cancellation, the host MUST retain `canceling` until a terminal worker result confirms that attempt's outcome. Check: `modules/hub/tests/integration/features/execution/flows/test_recovery.py::test_http_adapter_lost_response_and_cancel_tombstone`.
19. **Client transport**: WHEN the SDK sends an HTTP request, its client MUST send no automatic retry or redirect. Check: `packages/sdk/tests/test_remote_contract.py::test_client_does_not_follow_redirect_or_retry_and_normalizes_non_json_errors`.

## 4. Interfaces and Data Contracts

### HTTP API and authorization

All paths below include the `/api/v1` router prefix. Credentials use `X-API-Key`.
The first successful registration claims a provider/environment for its machine;
rotating keys for that machine preserves ownership.

| Operation | Method and path | Required scope | Success |
| --- | --- | --- | --- |
| Register | `PUT /api/v1/task-providers/{provider}/environments/{environment}/releases/{release_id}` | `autohub:task:write` | 200 `ReleaseReceipt` |
| Activate | `POST /api/v1/task-providers/{provider}/environments/{environment}/releases/{release_id}/activate` | `autohub:task:write` | 200 `ActivationReceipt` |
| Admit | `POST /api/v1/task-runs` | `autohub:task:write` | 202 `RunView` |
| Read | `GET /api/v1/task-runs/{run_id}` | `autohub:task:read` | 200 `RunView` |
| Command | `POST /api/v1/task-runs/{run_id}/commands` | `autohub:task:write`; also `autohub:task:approve` for approve/revise | 200 `RunView` receipt |

`ReleaseSpec` contains `FlowManifest` v2 (`tasks`, `flows`) and `bindings`.
Each binding names a task contract, `executor` (`http` or `native`) and a configured
`target`; registration uploads no Python code. Native targets are
`autohub.identity`. The former `autohub.sdd:*` and `autohub.pr_delivery:*`
bindings are retired under `CAP-SDK-existing-pr-bridge`. HTTP targets are server-configured through
`AUTOHUB_FLOW_HTTP_TARGETS` and require HTTPS or loopback HTTP. Their URLs reject
embedded usernames/passwords, query strings and fragments. The optional
`credential_env` name matches `^[A-Z][A-Z0-9_]*$`. Registration snapshots the
resolved URL and credential-variable name; changing those settings requires a
new release. The variable's value is read for each worker call rather than
stored in the release, allowing credential-value rotation independently.

`FlowManifest` v2 does not replace the SDK's local `Manifest` v1. Its task
definitions use `PipelineSpec`; `FlowSpec` declares input/output schemas, ordered
`steps` and a task `result_step`. A task step carries `kind: task`, `id`, `task`,
an `inputs` binding map and `max_attempts` (default 1). Each input is a literal
(`kind: literal`, `value`) or reference (`kind: ref`, `source`, `path`, optional
`step_id`). A `source: step` reference requires an earlier task's `step_id`;
`source: run` leaves `step_id` absent or null. `path` traverses object fields in the selected input or
task output. An approval step carries `kind: approval`, `id`,
`deadline_seconds` (default 86,400), `revise_to` and `max_revisions` (default 0).
An earlier task's `revise_to` and a positive `max_revisions` must be supplied
together. These models reject unknown fields.

Activation accepts `ActivationRequest.expected_revision`, a strict nonnegative
integer. `ReleaseReceipt` contains `provider`, `environment`, `release_id` and
`digest`; `ActivationReceipt` additionally contains the environment `revision`.
`ReleaseSpec.digest()` is SHA-256 over sorted-key compact UTF-8 JSON with
non-finite numbers rejected.

`RunRequest` contains `provider`, `environment`, `task` (`key`,
`contract_version`), `inputs` and `idempotency_key`. The host additionally accepts
optional `expected_release_id` and `expected_release_digest`; omitted fields keep
the SDK 0.2.0 request contract. An expected release ID is 1–128 characters and
an expected digest is exactly 64 lowercase hexadecimal characters.
`RunCommand` contains `command_id`, a strict nonnegative `expected_revision`
and `action` (`approve`, `revise`, `cancel`, `resume`).

Provider/environment identifiers match `^[a-z][a-z0-9_-]*$` and are at most 64
characters. Release IDs are 1–128 characters matching
`^[A-Za-z0-9][A-Za-z0-9_.-]*$`; request/command IDs are 1–128 characters. Task keys
are dot-separated identifiers, at most 256 characters; versions are positive
integers through 2,147,483,647. Step IDs are identifiers through 128 characters.
`max_attempts` is 1–10; `max_revisions` is 0–10; approval deadlines are 1–31,536,000
seconds. JSON values must be finite. Schemas use JSON Schema draft 2020-12 with
local `$ref`/`$dynamicRef` only; actual resolved task inputs and outputs are
validated at execution time.

The SDK client exposes HTTP failures as `AutoHubError.status` and
`AutoHubError.code`; non-JSON errors use `http-error`, and network timeouts
propagate to the caller. SDK 0.2.0 requires Python 3.13+ and Pydantic, without a
backend or database runtime dependency.

### Execution and worker protocol

Public run states are `queued`, `running`, `waiting`, `failed`, `canceling`,
`canceled`, `completed`; waiting reasons are `approval` and `external-result`.
`RunView` exposes run/release identity, task, revision, current step, attempts,
output and error. `AttemptView` exposes step ID, number, status, inputs, output
and error; persisted `intent`/`ready` states appear publicly as `running`.

Admission and GET do not execute workers. Maintenance selects up to 32 due runs
per batch and advances each once, using a 60-second lease. External-result polls
are scheduled at least 5 seconds later; this minimum does not promise wall-clock
completion before the scheduler next runs. An elapsed approval becomes
`failed` / `approval-deadline` when advancement records the expiry.

HTTP workers receive `POST /executions`, `GET /executions/{attempt_id}` and
`DELETE /executions/{attempt_id}` with `Idempotency-Key: <attempt_id>`.
If `credential_env` is configured, each request additionally sends `X-API-Key`
from that environment variable. All three calls use a five-second timeout and
disable redirects. Missing configured credentials stop the call through the
recoverable worker-error path.
Submission includes `attempt_id`, `run_id`, `task`, `inputs`, `release_id` and
`release_digest`. The worker returns matching `attempt_id`, `status`
(`pending`, `completed`, `failed`, `canceled`, `not_found`), optional `output` and
`error`; completed results require output. Only inspection can authorize
`not_found`, including a structured matching 404 response. Network/HTTP/protocol
errors do not prove absence or cancellation.

The external worker owns durable idempotent attempt receipts and cancellation
tombstones. A cooperating worker validates the requested task/release identity
and prevents a later submission of an attempt canceled before it was known.
The host checks response identity and schema, not the worker's internal receipt
storage or release validation. Terminal completion/failure can acknowledge a
cancellation while preserving evidence of an effect that already happened;
an unstructured DELETE 404 cannot. This cooperation does not establish
exactly-once external effects. Recovery fixtures simulate worker receipts and
cancellation responses rather than proving an arbitrary deployed worker.

### Errors

HTTP errors use `{code, message}`. Worker outcomes are recorded in `RunView.error`
and are not themselves HTTP refusal responses.

| HTTP | Codes and condition |
| --- | --- |
| 401 | `unauthorized`: missing managed machine key |
| 403 | `task-scope`: missing scope; `environment-owner`: foreign machine |
| 404 | `environment-not-found`, `release-not-found`, `task-not-found`, `run-not-found`: missing named entity |
| 409 | `release-conflict`, `request-conflict`, `command-conflict`: reused identity with changed content |
| 409 | `stale-revision`: environment/run revision changed; `release-mismatch`: expected release changed; `no-active-release`: no activated release |
| 409 | `approval-expired`, `revision-limit`, `attempt-limit`, `invalid-command`: disallowed transition |
| 422 | `request-invalid`: wire schema; `contract-limit`: host bound; `json-invalid`: non-finite JSON; `schema-reference` or `schema-invalid`: invalid schema/value; `worker-binding`: unconfigured target |

Asynchronous errors include `worker-unavailable` (retained for inspection/retry),
`input-reference`, `schema-invalid`, `worker-output-invalid`,
`flow-output-invalid`, `approval-deadline`, `attempt-limit` and worker-provided
failure errors. Run/step/attempt/command records live in separate `sdk_flow_*`
tables rather than scheduler history or PR attempts.

The HTTP adapter's internal `worker-credentials` and `worker-protocol` errors
are caught by the host worker and exposed as `worker-unavailable` on the run;
they are not direct refusal codes from the run API. SDK release/run/attempt/
command records have no automatic retention policy: the maintenance retention
path prunes scheduler jobs, PR runs and webhook deliveries instead.

## 5. Source and Verification Evidence

The contracts above were checked by inspecting the SDK's
[flow models](../../../packages/sdk/src/autohub_sdk/flow.py),
[remote models](../../../packages/sdk/src/autohub_sdk/remote.py),
[client](../../../packages/sdk/src/autohub_sdk/client.py), and the host's
[API](../../../modules/hub/app/features/execution/flows/api.py),
[service](../../../modules/hub/app/features/execution/flows/services.py),
[runtime](../../../modules/hub/app/features/execution/flows/runtime.py),
[worker](../../../modules/hub/app/features/execution/flows/worker.py),
[repository](../../../modules/hub/app/features/execution/flows/repos.py),
[adapters](../../../modules/hub/app/features/execution/flows/adapters.py) and
[maintenance retention](../../../modules/hub/app/features/execution/tasks/domains/maintenance/retention.py).
The named tests were inspected as enforcing evidence; authoring this document did
not execute them or establish live provider/GitHub behavior. The PostgreSQL
concurrency test requires PostgreSQL and does not pass by being skipped on SQLite.
