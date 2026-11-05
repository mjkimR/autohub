# Developing Auto Hub

This directory covers changes to Auto Hub itself: the contributor environment,
code generation, tests, dependency updates and extension points. Product behavior
belongs in capability/use-case contracts; deployed-service setup and recovery
belong in [operations](../operations/README.md).

## Environment and commands

Run project commands from the repository root. Use Python 3.13+, uv, just and the
Node version in `.nvmrc`. Initialize the backend even for frontend-only work:

```sh
just init
just dev-run hub
just dev-run hub-ui
```

The UI runs on port 5173 and proxies `/api` to `http://127.0.0.1:8389`.
Use module arguments `hub`, `hub-ui` or `sdk` for targeted initialization/checks.
The root [justfile](../../justfile) owns command syntax and defaults.

| Work | Contributor command |
| --- | --- |
| Format/lint | `just lint`; read-only equivalent: `just lint-check` |
| Python/UI types and production UI build | `just check` |
| Backend or UI tests | `just test`, `just test-ui`; see [test selection](testing.md) |
| Standalone SDK | `just test-sdk`, `just build-sdk` |
| Regenerate typed UI API | `just gen-ui-api`; verify with `just check-ui-api` |
| Generate a migration | `just db-revision "Describe the schema change"` |
| Apply local migrations | `just db-upgrade` |

Check recipes already use `devkit run`, printing bounded output and a complete
log path; do not wrap them again. Frontend recipes activate `.nvmrc` through nvm
when available. Install that Node version before invoking them.

Follow `ARCH-02-constraints` for dependency/transaction boundaries and
`ARCH-05-2-components` for code ownership. The frontend consumes generated typed
API resources; [its guide](../../modules/hub-ui/README.md) owns generation details
and data-loading/session conventions.

## Register a task

Put task-specific behavior under `app/features/execution/tasks/domains/<domain>`.
Use the existing registry with a Pydantic payload:

```python
from app.features.execution.tasks import task
from app.features.execution.tasks.core.log import logger
from pydantic import BaseModel

class EchoPayload(BaseModel):
    message: str

@task(name="example.echo")
async def echo(payload: EchoPayload) -> None:
    logger.info(payload.message)
```

Import the domain in `app/features/execution/tasks/domains/__init__.py` so startup
autodiscovery registers it. Keep task orchestration separate from shared scheduler
implementation. Use the task logger for execution-context logs and
`app_layer_base.core.log` for application logging; omit credentials and PII.
Scheduler guarantees belong in `CAP-EXEC-scheduling-maintenance`.

## Local authentication configuration

Use the ordinary signed-in UI for local development. To exercise Google callbacks
through the Vite proxy, set both frontend and callback origins to
`http://localhost:5173`, retain `/api/v1/auth/google/callback` as the callback path,
and set `GOOGLE_AUTH_COOKIE_SECURE=false` only for this local HTTP setup.
Production identity-provider and cookie setup belongs in
[access operations](../operations/access.md).

## Contributor guides

- [Testing and CI](testing.md): execution tiers, isolated SDD contracts and optional fixture environments.
- [Dependency and asset updates](toolchain.md): published refs, runtime locks, viewer artifacts and generated receipts.
- [Provider extensions](provider-extensions.md): quota kinds, transport adapters and connection-test recipes.
- [Documentation changes](documentation.md): authoring sources, ownership and document validation.

Before completing changes, run `just lint`, `just check` and relevant tests.
Report the checks actually executed and any unverified integration boundaries.
