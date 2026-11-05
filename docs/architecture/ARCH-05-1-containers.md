---
id: ARCH-05-1-containers
title: Containers and code ownership
summary: "Maps the backend, SPA, database, isolated SDD runtime and standalone SDK to their code and dependency boundaries."
status: active
---

# [ARCH-05-1-containers] Containers and code ownership

## Runtime building blocks

```mermaid
flowchart TB
    Browser[Browser SPA] -->|Typed HTTP API| API[FastAPI application]
    Client[SDK or MCP client] --> API
    API --> DB[(PostgreSQL)]
    API --> Runtime[OS-isolated devkit process]
    API --> External[GitHub, providers and configured workers]
    Image[Deployment image] --- API
    Image --- Assets[Compiled SPA assets]
    Image --- Runtime
```

The diagram separates logical runtime blocks. The standard image serves both the
API and compiled SPA, and contains both reviewed SDD runtime profiles.

| Block | Code or configuration | Owned responsibility |
| --- | --- | --- |
| Backend | `modules/hub/app` | HTTP/MCP adapters, execution coordination, durable state and provider integrations |
| SPA | `modules/hub-ui/src` | Operator views, browser session state and typed API consumption |
| Database | `modules/hub/migrations`, `app/common/database_schema.py` | Application records, leases, revision fences and migration-managed structure |
| SDD process | `app/features/project_management/sdd`, `config/sdd-runtime*` | Disposable repository evaluation with reviewed CLI/package identity |
| Standalone SDK | `packages/sdk/src/autohub_sdk` | Local declarations, manifests and typed remote client contracts |

## Backend decomposition

`ARCH-05-2-components` owns the internal feature responsibilities, provider ports
and registries. The task registry is exposed from `app/features/execution/tasks`;
startup invokes its autodiscovery. `app/features/__init__.py` re-exports this
entrypoint rather than introducing another task implementation.

## Dependency direction

The backend consumes `autohub-sdk`; the SDK does not import the backend or its
database. The SDK manifest declares Pydantic as its runtime dependency. Repository
SDD environments are provisioned separately from the backend environment, and
requests do not install a target repository's dependency set.

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
