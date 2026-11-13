---
id: ARCH-07-deployment
title: Deployment and runtime isolation
summary: "Defines the container build, migration startup, database namespace and the per-instance cache of repository-locked devkit runtimes used by Auto Hub."
status: active
---

# [ARCH-07-deployment] Deployment and runtime isolation

## Deployment artifact

[docker/hub.Dockerfile](../../docker/hub.Dockerfile) builds the SPA with Node 24,
installs the pinned build environment `/opt/sdd-build` (hatchling from
`config/sdd-build`) and installs the backend workspace's production dependencies
with Python 3.13. The final image copies compiled UI assets, backend code, Alembic
migrations, `/opt/sdd-build` and the build stage's `uv` binary, and installs Git
and bubblewrap. It sets `AUTOHUB_SDD_BUILD=/opt/sdd-build` and
`AUTOHUB_SDD_CACHE=/tmp/autohub-sdd-runtimes`. The image contains no devkit
runtime and its build needs no source credential. It runs as the non-root
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

## Repository SDD runtime

Each evaluation installs, on first use per instance, the devkit runtime that the
evaluated commit's root `uv.lock` pins (`ADR-repository-locked-runtime`). The Hub
process fetches locked GitHub sources with the project's connector token and
installs hashed PyPI wheels; sandboxed steps build the sources offline with
`/opt/sdd-build` and install them (`ADR-offline-source-build`). Entries are
published atomically into `AUTOHUB_SDD_CACHE`, leased by evaluations and evicted
above `AUTOHUB_SDD_CACHE_BYTES` (256 MiB by default). The cache is per instance and
does not survive a restart; on Cloud Run `/tmp` is in-memory and counts against
the instance's memory.

An install runs as a background task in the worker process that claimed it;
callers receive `SDD_RUNTIME_PREPARING` until it completes. With request-based
CPU allocation, Cloud Run throttles CPU between requests and can slow that task;
`SPEC-repo-locked-sdd-runtime` assumes scheduled dispatcher requests let it
progress, which has not been observed on the serving host. The deployment does not
change CPU allocation for it.

Constraints:

- Serving hosts MUST run Linux with bubblewrap and unprivileged user namespaces.
  Check: the runtime status host probe on the serving host (operational, not CI);
  macOS sandbox-exec is local development only.
- Repository build and evaluation code MUST NOT receive host credentials or
  network access. Check: `modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py`,
  `test_source_build_hook_cannot_reach_the_network_or_credentials`;
  `modules/hub/tests/integration/features/project_management/sdd/test_cli.py`,
  `test_repository_python_rule_cannot_read_host_secret_or_use_network`.
- The Hub process MUST be able to reach `https://github.com/` and PyPI. Check:
  Review only.

Native evaluation uses disposable checkouts and an OS-isolated process. Git and
CLI publication have distinct credential boundaries. A changed runtime identity
continues an admitted run; changed workflow, policy or configuration identity does
not. `CAP-SDD-runtime-isolation` owns runtime selection, installation, readiness
and restoration; `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` own
repository lifecycle actions.

## Operational evidence boundary

A successful local build or isolation fixture does not establish the currently
serving revision, real provider replies or a live merge. Use the
[deployment procedure](../operations/cloud-run-deployment.md),
[runtime operations guide](../operations/sdd-runtime.md) and
[delivery status](../operations/deployment-status.md) for actual operations and
recorded verification. This document describes the source-defined deployment
structure; it does not assert a new deployment.
