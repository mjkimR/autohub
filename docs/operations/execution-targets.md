# SDK execution targets

Use this guide to configure a serving Auto Hub host before registering SDK
releases. `CAP-SDK-task-flow-execution` owns the API/worker protocol and
`CAP-SDK-existing-pr-bridge` owns PR evidence and approval. Configuration does
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
Native `autohub.identity` is available for a pure input-echo contract check;
configured bridge targets use the procedure below.

## SDK flow bridge with an existing PR

Check the [serving host](sdd-runtime.md#serving-host) before configuring bridge
targets. Mount or otherwise provision a clean checkout on the Hub host whose HEAD
matches the PR being reviewed and whose root `uv.lock` meets the
[consumer requirements](sdd-runtime.md#consumer-requirements). The standard image
packages Git, `uv` and the pinned build environment, but does not provision that
repository checkout for the bridge.

Set a server-owned delivery mapping before registering the consumer's release:

```sh
AUTOHUB_FLOW_DELIVERY_TARGETS='{"local":{"provider":"planhub","environment":"local","project_id":"<existing-project-uuid>","checkout":"/absolute/clean/checkout"}}'
```

This example permits `autohub.sdd:local` and `autohub.pr_delivery:local` for the
named provider/environment and existing project. The checkout path must be
absolute. The check uses the devkit runtime the checkout's own lock pins; the
project's GitHub connector must be able to read that lock's Git sources. Release
registration installs neither the runtime nor checkout dependencies; the first
check of an uncached lock starts the runtime install.

Check the mounted checkout and intended existing paused PR run before submitting
the flow. Review the evidence through `UC-resume-verified-pr` and use a machine
key carrying approval scope for the approval command. Approval does not itself
mark the PR ready or replace the existing PR owner's CI/merge controls.
Resolve an unsuccessful delivery against that owner explicitly; do not treat
an uncertain result as permission to create another PR executor.

## Operational verification

Confirm the target mapping and credential-variable availability on the serving
host, then register and activate the intended release. Observe run and attempt
results through `UC-execute-task-flow` or `UC-resume-verified-pr`. A successful
local fixture or echo task does not prove a bridge's deployed GitHub, approval,
CI or merge path. Record live evidence and its source/release identity in
[delivery status](deployment-status.md).

Contributor test commands and optional loopback applications belong in
[testing](../development/testing.md). Worker implementation and deployed service
credentials remain operator-owned.
