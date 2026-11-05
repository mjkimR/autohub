---
id: ARCH-07-deployment
title: Deployment and runtime isolation
summary: "Defines the container build, migration startup, database namespace and separately provisioned devkit runtime used by Auto Hub."
status: active
---

# [ARCH-07-deployment] Deployment and runtime isolation

## Deployment artifact

[docker/hub.Dockerfile](../../docker/hub.Dockerfile) builds the SPA with Node 24,
provisions the reviewed default/app-common SDD profiles, and installs the backend
workspace's production dependencies with Python 3.13. The final image copies
compiled UI assets, backend code, Alembic migrations and both runtime directories.
It runs as the non-root `appuser`.

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

## Repository SDD runtime

The reviewed profiles are provisioned before serving requests. A server-owned
repository mapping chooses the profile; target repositories do not supply
installation manifests during an operation. The default image contains
`/opt/sdd` and `/opt/sdd-app-common`.

Native evaluation uses disposable checkouts and an OS-isolated process. Git and
CLI publication have distinct credential boundaries. Runtime pin/profile changes
are not an in-place upgrade of an admitted run's workflow/approval identity.
`CAP-SDD-runtime-isolation` owns runtime readiness and restoration;
`CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` own repository lifecycle
actions.

## Operational evidence boundary

A successful local build or isolation fixture does not establish the currently
serving revision, real provider replies or a live merge. Use the
[deployment procedure](../operations/cloud-run-deployment.md),
[runtime provisioning guide](../operations/sdd-runtime.md) and
[delivery status](../operations/deployment-status.md) for actual operations and
recorded verification. This document describes the source-defined deployment
structure; it does not assert a new deployment.
