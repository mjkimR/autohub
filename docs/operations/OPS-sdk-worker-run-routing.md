---
id: OPS-sdk-worker-run-routing
title: "SDK HTTP worker run diagnosis and routing"
status: active
summary: "Routes an SDK flow release or run bound to a generic HTTP worker that is refused, stays waiting or canceling, or fails, to its existing owner through the API refusal code, RunView status and error, the latest attempt status and the scheduler trigger; worker internals stay outside Hub evidence."
related_capabilities:
  - CAP-SDK-task-flow-execution
  - CAP-EXEC-scheduling-maintenance
related_usecases:
  - UC-execute-task-flow
---

# [OPS-sdk-worker-run-routing] SDK HTTP worker run diagnosis and routing

An SDK flow run bound to an `http` executor can sit in `waiting` for a long time, stay `canceling` after a cancel
command, or fail while the worker application looks healthy from its own side. Hub records every transport,
credential and protocol problem on the run as the same `worker-unavailable` error, and it does not log those
causes, so the run error alone cannot tell a missing credential, an unreachable worker, a protocol mismatch and a
stopped scheduler apart. Admission and `GET` never execute a worker; only shared maintenance advances runs
(`CAP-SDK-task-flow-execution` §4, Execution and worker protocol).

## Routing

`GET /api/v1/task-runs/{run_id}` returns `RunView` with `status`, `waiting_reason`, `error`, `revision` and
`attempts[]`, each attempt carrying `status` and `error`. An attempt whose intent Hub has persisted but not yet
settled shows `running`; an attempt the worker reported as `pending` shows `observing`. API refusals use
`{code, message}` (`CAP-SDK-task-flow-execution` §4, Errors).

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| Every SDK flow route fails, including run reads | HTTP 500 without a flow `code` on every `/api/v1/task-providers/...` and `/api/v1/task-runs/...` call; the server log shows a validation error for `AUTOHUB_FLOW_HTTP_TARGETS` (malformed JSON, a non-HTTPS non-loopback URL, or a URL with credentials, query or fragment) | [HTTP worker configuration](../runbooks/execution-targets.md#http-worker-configuration); `CAP-SDK-task-flow-execution` §4, HTTP API and authorization, owns the target URL rules. |
| Release registration refused for its binding | `422 worker-binding`: the binding names a `target` absent from the serving process's `AUTOHUB_FLOW_HTTP_TARGETS`, or a native target other than `autohub.identity` | [HTTP worker configuration](../runbooks/execution-targets.md#http-worker-configuration); `UC-execute-task-flow` extension 1a. |
| Other registration, activation, admission or command refusal | Any other `{code, message}` refusal listed in the capability error table, such as `task-scope`, `environment-owner`, `release-mismatch` or `stale-revision` | `CAP-SDK-task-flow-execution` §4, Errors, and the matching `UC-execute-task-flow` extension; [SDK flow host](../runbooks/execution-targets.md#sdk-flow-host) for scopes and machine ownership. |
| Run waits on an unreachable or nonconforming worker | `status` `waiting`, `waiting_reason` `external-result`, `error` `worker-unavailable`, latest attempt `running`; the worker's access log has no request with `Idempotency-Key: <attempt_id>`, rejects its `X-API-Key`, or answers with a non-2xx status, a mismatched `attempt_id` or an unstructured inspect 404; the Hub process may lack the variable named by `credential_env` | [HTTP worker configuration](../runbooks/execution-targets.md#http-worker-configuration) for the target and credential; `CAP-SDK-task-flow-execution` §4, Execution and worker protocol, owns the request and response contract; `UC-execute-task-flow` extension 4a. |
| Run waits on a worker that accepted the attempt | `status` `waiting`, `waiting_reason` `external-result`, latest attempt `observing`, `error` null or worker-provided | The operator of the worker application, which owns its execution and durable receipts (`CAP-SDK-task-flow-execution` §2, Out-of-Scope). |
| Run calls the previous worker URL or credential variable after a configuration change | The worker named in the old configuration still receives the run's requests; the run's `release_id` is the release registered before the change | [HTTP worker configuration](../runbooks/execution-targets.md#http-worker-configuration) (new release ID and activation); `CAP-SDK-task-flow-execution` §3 rule 7 owns the admission snapshot. |
| Cancellation does not finish | `status` stays `canceling`; `error` `worker-unavailable` means the cancel call itself does not reach a conforming worker, otherwise the worker keeps answering `pending` or an unstructured 404 to `DELETE /executions/{attempt_id}` | `CAP-SDK-task-flow-execution` §3 rule 18 and §4, Execution and worker protocol, for the cancellation contract; the worker operator for its cancellation tombstone; the unreachable-worker row above for `worker-unavailable`. |
| Task fails on worker output | `status` `failed`, `error` `worker-output-invalid`; the failed attempt retains the worker output | The worker operator against the task's declared output schema; `CAP-SDK-task-flow-execution` §3 rule 17; `UC-execute-task-flow` extension 6a. |
| Task fails as reported by the worker | `status` `failed`, `error` `worker-failed`, `worker-canceled` or a worker-provided error string; the attempt status is `failed` or `canceled` | The worker operator; `UC-execute-task-flow` extension 4b for a permitted explicit `resume`. |
| Run fails on its flow contract | `status` `failed`, `error` `input-reference`, `schema-invalid`, `flow-output-invalid`, `attempt-limit` or `approval-deadline` | `CAP-SDK-task-flow-execution` §4, Errors, and `UC-execute-task-flow` extensions 4b, 5c and 6a; the release author, not the worker. |
| Run does not move at all | `revision` and the latest attempt stay unchanged across several minutes while the run is `queued`, `running` or due for an external-result poll; System › Health shows the scheduler trigger as Stopped or Never fired, or `system.maintain` jobs fail | [Check whether the trigger is firing](../runbooks/operator-notices.md#check-whether-the-trigger-is-firing); [Logs and expired history](../runbooks/operator-notices.md#logs-and-expired-history) for a failed maintenance job; `CAP-EXEC-scheduling-maintenance` owns the maintenance schedule. |

Read `RunView` before the worker's logs, because `status`, `error` and the latest attempt status already separate
the rows. For evidence that matches no row, take the `RunView.error` or refusal `code` to its entry in
`CAP-SDK-task-flow-execution` §4, Errors.

## Normal-state observation

After the owner's action, the next maintenance passes move the run off `worker-unavailable`: the latest attempt
becomes `observing`, `completed` or a worker-reported terminal status, `revision` advances, and the run reaches
`completed` with `output` or waits on `approval`. The worker's access log shows the attempt's requests carrying its
`Idempotency-Key`. `CAP-SDK-task-flow-execution` owns these states; `CAP-EXEC-scheduling-maintenance` owns the
maintenance cadence that drives them.

## Authority boundary

Hub checks response identity and schema only. The evidence cannot establish that the worker validated the task or
release identity, kept durable receipts or produced an external effect exactly once
(`CAP-SDK-task-flow-execution` §4, Execution and worker protocol). Because the host does not log the cause of
`worker-unavailable`, only the worker's own logs and the Hub process's environment separate its causes.
`CAP-ACCESS-authentication-authorization` owns machine-key provisioning and scopes.

## Update triggers

- `CAP-SDK-task-flow-execution` §3 rules 7, 17 or 18, or §4 Execution and worker protocol or Errors change.
- `RunView.status`, `waiting_reason`, `error` or `AttemptView.status` values change.
- The error mapping in
  [worker.py](../../modules/hub/app/features/execution/flows/worker.py) or the target parsing and response checks in
  [adapters.py](../../modules/hub/app/features/execution/flows/adapters.py) change.
- SDK flow advancement moves out of the `system.maintain` task.
