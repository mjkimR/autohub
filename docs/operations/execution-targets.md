# SDK execution targets

Use this guide to configure a serving Auto Hub host before registering SDK
releases. `CAP-SDK-task-flow-execution` owns the API/worker protocol and
`CAP-SDK-existing-pr-bridge` identifies retired built-in bridge bindings. Configuration does
not create a release, deploy worker code or prove a live delivery.

## SDK flow host

Deploy the backend and its matching migrations. The flow ledger was introduced
by migration `d69f762c5465`; the existing-PR bridge adds `e70a873d6576`. The normal
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

## Retired built-in PR bridge

The `autohub.sdd:*` and `autohub.pr_delivery:*` namespaces reject new effects with
`SDD_BRIDGE_RETIRED`. Do not provision an operator checkout, devkit runtime or
`AUTOHUB_FLOW_DELIVERY_TARGETS` mapping for them. Existing idempotent history
replays can return retained outcomes. Exact receipt-backed delivery can observe
its old PR owner without a second resume; unreceipted work retires terminally.
Completed results stay readable. `CAP-SDK-existing-pr-bridge` owns these bounds.

## Operational verification

Confirm the configured HTTP target and credential-variable availability, then
register/activate the intended generic release. Observe run/attempt results
through `UC-execute-task-flow`. Local echo/fixture results do not prove another
worker's deployed receipt protocol or live GitHub behavior. Record live evidence
and source/release identity in [delivery status](deployment-status.md).

Contributor checks belong in [testing](../development/testing.md). Worker
implementation and deployed service credentials remain operator-owned.
