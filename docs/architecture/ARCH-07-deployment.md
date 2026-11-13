---
id: ARCH-07-deployment
title: Deployment and external execution boundary
summary: "Defines the container build, migration startup, database namespace and external repository-execution boundary used by Auto Hub."
status: active
---

# [ARCH-07-deployment] Deployment and external execution boundary

## Deployment artifact

[docker/hub.Dockerfile](../../docker/hub.Dockerfile) builds the SPA with Node 24,
installs the backend workspace's production dependencies
with Python 3.13. The final image copies compiled UI assets, backend code, Alembic
migrations and the runtime dependencies needed by the backend. It contains no
SDD build environment, runtime cache or evaluation sandbox tooling. It runs as the non-root
`appuser`.

[docker/run_hub.sh](../../docker/run_hub.sh) applies `alembic upgrade head` before
starting the FastAPI factory with Uvicorn. The container reads `PORT`; worker
count defaults to three. Startup failure while applying migrations prevents the
server command from running.

The application serves the SPA when a valid UI distribution exists. Otherwise
its root redirects to API documentation. Protected MCP mounts precede the SPA
fallback, and well-known discovery paths do not receive the SPA shell.
`modules/hub/tests/integration/test_main.py` checks these route boundaries and
OpenAPI independence from UI build availability.

## Database namespace

PostgreSQL deployments can select `DB_SCHEMA`. The identifier is lowercase,
at most 63 characters and excludes reserved application/platform namespaces.
Migration setup creates the namespace and selects it for reflection/versioning.
Runtime transactions set a local `search_path`; a missing configured schema
fails rather than falling back to another namespace.

SQLite and PostgreSQL without `DB_SCHEMA` retain their default behavior.
[Schema configuration](../../modules/hub/app/common/database_schema.py),
[unit tests](../../modules/hub/tests/unit/common/test_database.py) and
[PostgreSQL integration tests](../../modules/hub/tests/integration/common/test_database.py)
anchor this boundary. SQLite tests do not prove PostgreSQL schema behavior.

## Deployment boundary

The serving image MUST carry no connected-repository SDD evaluator, installer,
lock-derived cache, pinned source-build environment or evaluation sandbox
requirement. Check: `docker/hub.Dockerfile`, CI/recipe inspection and
`CAP-SDD-native-delivery` retired-surface tests.

The Hub process uses GitHub/provider connections for publication and observation.
It does not fetch devkit packages or repository build sources. The working agent
owns repository setup and workflow execution; configured repository verification
runs in GitHub Actions. Auto Hub's contributor devkit environment stays separate.

Old `AUTOHUB_SDD_*` cache/build/profile variables and sandbox-host probes are not
serving prerequisites. The retired built-in SDK bridge needs no mounted checkout
or `AUTOHUB_FLOW_DELIVERY_TARGETS` mapping. Generic HTTP worker targets retain
`CAP-SDK-task-flow-execution` and their configured credential boundary.

## Operational evidence boundary

A successful local build or fixture does not establish the currently
serving revision, real provider replies or a live merge. Use the
[deployment procedure](../operations/cloud-run-deployment.md),
[activity operations guide](../operations/sdd-runtime.md) and
[delivery status](../operations/deployment-status.md) for actual operations and
recorded verification. This document describes the source-defined deployment
structure; it does not assert a new deployment.
