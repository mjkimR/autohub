# SDK execution targets

Use this guide to configure a serving Auto Hub host before registering SDK
releases. `CAP-SDK-task-flow-execution` owns the API/worker protocol and
`CAP-SDD-native-delivery` separately owns repository activity starts. Configuration does
not create a release, deploy worker code or prove a live delivery.

## SDK flow host

Deploy the backend and its matching migrations. The flow ledger was introduced
by migration `d69f762c5465`; `d704fb51a433` removes unused built-in bridge link storage. The normal
container entrypoint applies `alembic upgrade head` before serving requests.
For a manually managed environment, run `just db-upgrade` from the repository
root against the intended database. Follow the
[deployment procedure](cloud-run-deployment.md) for the serving host.

Issue a managed machine key with `autohub:task:write` for registration,
activation, submission and control, and `autohub:task:read` for polling.
Approve/revise commands additionally need `autohub:task:approve`.
`autohub:dispatch` alone grants no task/flow access. Use the same registered
machine across key rotation because provider/environment ownership belongs to
the machine that first registered it. Access provisioning belongs to
`CAP-ACCESS-authentication-authorization`.

### HTTP worker configuration

Provision the worker application separately and configure the Hub process's
server environment before registering a release:

```sh
AUTOHUB_FLOW_HTTP_TARGETS='{"planhub-worker":{"base_url":"https://worker.example","credential_env":"PLANHUB_WORKER_KEY"}}'
```

Supply `PLANHUB_WORKER_KEY` through the deployment's secret configuration; keep
its value out of release JSON. A release then selects executor `http` and target
`planhub-worker`. Use HTTPS except for loopback test workers, and omit embedded
credentials, query strings and fragments from the URL.

The serving process parses `AUTOHUB_FLOW_HTTP_TARGETS` on every SDK flow API
request. If the value is not valid JSON, or a target URL breaks the rules above,
every route under `/api/v1/task-providers/...` and `/api/v1/task-runs/...`
returns a generic HTTP 500 without a flow `code`, including run reads. Look for
the validation error in the server log and correct the variable. A well-formed
value that lacks the release's target name instead refuses registration with
`422 worker-binding`.

The worker implements the submit/inspect/cancel interface in
`CAP-SDK-task-flow-execution`, including durable receipt and cancellation
handling. Check that its configured task/release validation agrees with the
release being registered. The host's response checks do not validate the
worker's internal storage or implementation.

A release snapshots its resolved URL and credential-variable name. When changing
those settings, register a new release ID and activate it at the observed
environment revision; an existing release replay preserves the original binding.
Rotating the referenced credential's value does not require a new release.
Native `autohub.identity` is available for a pure input-echo contract check.

### Diagnose an unavailable worker

A run that shows `status` `waiting`, `waiting_reason` `external-result` and
`error` `worker-unavailable` did not get a usable worker response. Hub records
these causes under that one error and does not log which one occurred:

- the Hub process lacks the variable named by `credential_env`;
- the worker is unreachable or exceeds the five-second timeout;
- the worker answers with a non-2xx status or a redirect;
- the response breaks the protocol, such as a mismatched `attempt_id`, an invalid
  body or an unstructured 404 on inspection.

The run keeps the same attempt and schedules another try at least 5 seconds
later, taken up by the next maintenance pass. These retries do not consume
`max_attempts`, so the run waits until the cause is repaired or the run is
canceled.

1. Confirm that the serving Hub process has the variable named by
   `credential_env` set to a nonempty value.
2. Search the worker's access log for requests carrying
   `Idempotency-Key: <attempt_id>`. No request means a URL, network or
   credential-variable problem on the Hub side; a rejected `X-API-Key` or a
   non-2xx answer points to the worker's configuration.
3. Compare the worker's responses with the protocol in
   `CAP-SDK-task-flow-execution`.

`OPS-sdk-worker-run-routing` routes the other run states.

## Repository activities

Use repository-owned SDD activity starts or ordinary PR enrollment for repository
work. Generic SDK workers have no built-in PR delivery bridge.
