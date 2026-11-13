---
id: ARCH-05-1-containers
title: Containers and code ownership
summary: "Maps the backend, SPA, database, external repository execution and standalone SDK to their code and dependency boundaries."
status: active
---

# [ARCH-05-1-containers] Containers and code ownership

## Runtime building blocks

```mermaid
flowchart TB
    Browser[Browser SPA] -->|Typed HTTP API| API[FastAPI application]
    Client[SDK or MCP client] --> API
    API --> DB[(PostgreSQL)]
    API --> External[GitHub, providers and configured workers]
    Agent[Repository agent] --> Repository[Repository setup and workflow]
    Repository --> Actions[Repository GitHub Actions]
    API -->|Observe CI| Actions
    Image[Deployment image] --- API
    Image --- Assets[Compiled SPA assets]
```

The image serves the API and compiled SPA. Connected-repository work executes
outside Hub; there is no devkit evaluator process, runtime cache or source-build
container. `ADR-repository-owned-sdd-execution` records that boundary.

| Block | Code or configuration | Owned responsibility |
| --- | --- | --- |
| Backend | `modules/hub/app` | HTTP/MCP adapters, coordination, durable state and provider integrations |
| SPA | `modules/hub-ui/src` | Operator views, browser sessions and typed API consumption |
| Database | `modules/hub/migrations`, `app/common/database_schema.py` | Records, leases, revision fences and migration-managed structure |
| Repository agent and Actions | Connected repository/provider | Repository setup, workflow execution and configured verification |
| Standalone SDK | `packages/sdk/src/autohub_sdk` | Declarations, manifests and typed remote client contracts |

## Backend decomposition

`ARCH-05-2-components` owns the internal feature responsibilities, provider ports
and registries. The task registry is exposed from `app/features/execution/tasks`;
startup invokes its autodiscovery. `app/features/__init__.py` re-exports this
entrypoint rather than introducing another task implementation.

## Dependency direction

The backend consumes `autohub-sdk`; the SDK does not import the backend or its
database. The SDK manifest declares Pydantic as its runtime dependency. Repository
setup and workflow execution are external to Hub. Auto Hub's own contributor
devkit dependencies do not provision an evaluator for connected repositories.

The shared devkit-viewer component renders documents through a Hub-provided
authenticated repository data source. Its source receipt and rebuild procedure
remain in `modules/hub-ui/vendor/devkit-viewer.md`; product behavior belongs in
`CAP-DOC-repository-viewer`.

The frontend consumes generated declarations under `src/lib/api/generated` and
uses the shared API/session client. Code-generation details remain in the
[UI guide](../../modules/hub-ui/README.md).

## Code anchors and checks

- [Backend manifest](../../modules/hub/pyproject.toml) and
  [SDK manifest](../../packages/sdk/pyproject.toml) define dependency ownership.
- [Task entrypoint](../../modules/hub/app/features/execution/tasks/__init__.py)
  and [startup](../../modules/hub/app/main.py) define registration and lifecycle.
- [SDK tests](../../packages/sdk/tests) exercise declarations and client contracts.
- [Generated API freshness script](../../scripts/gen-ui-api.sh) backs `just check-ui-api`.

Structural constraints and their enforcement belong in `ARCH-02-constraints`.
