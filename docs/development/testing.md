# Testing and CI

Initialize the environment through the [development guide](README.md). Use the
root recipes rather than assembling different lint/type/test commands.
[Backend test conventions](../../modules/hub/tests/README.md) define execution
tiers and source-mirroring ownership; frontend tests remain beside their source.

## Select checks by change

| Boundary | Commands |
| --- | --- |
| Isolated backend logic | `just test-unit` or `just test tests/unit/features/<owner>` |
| Real DB and in-process API | `just test-integration` or an owning `tests/integration` path |
| All backend coverage | `just test` |
| PostgreSQL locks, persistence and migrations | `just test-pg` with the relevant path; Docker/testcontainers required |
| Frontend | `just test-ui`; use `just check hub-ui` for types/build |
| SDK without backend fixtures | `just test-sdk`, `just build-sdk` |
| Typed API freshness | `just check-ui-api` after `just gen-ui-api` |

`just test` uses SQLite by default. Unit doubles and SQLite do not prove
PostgreSQL lock contention or real provider behavior. The repository has no
deployed-process e2e suite; live canaries are operator procedures, not an empty
passing test target.

SQLite backend recipes use `pytest-xdist` CPU detection (`-n auto`) with at most
eight workers and work stealing. Each worker owns its in-memory database. `just test-unit` stays serial because
its short tests cost less than worker startup and repeated collection.
PostgreSQL recipes also stay serial by default to avoid extra containers.
Set `PYTEST_WORKERS` to select another worker count or run a focused test serially:

```sh
PYTEST_WORKERS=0 just test tests/integration/features/project_management/work_plans
PYTEST_WORKERS=2 just test
PYTEST_OPTIONS='-q --tb=short --durations=20' just test
```

Parallel PostgreSQL workers use separate Testcontainers instances. A shared
`AUTOHUB_FLOW_TEST_POSTGRES_URL` requires `PYTEST_WORKERS=0`; the runner rejects
parallel use of that database. SDK tests stay serial, and Vitest manages frontend
parallelism separately.

Work-plan tests using mock GitHub publication replace only Issue synchronization's
pacing sleep with an event-loop yield. Production pacing and real timeout
cancellation remain active outside that test double.

For shared fixtures, read the installed app-common testing guide after
`just init hub`, or run `uv run devkit app guide show testing`.
Vitest caches transformed modules but still executes tests. To compare without
the transform cache, use the repository's Node version and run:

```sh
npm --prefix modules/hub-ui test -- --fsModuleCache=false
```

## Isolated SDD contracts

Provision both reviewed profiles locally. A changed lock requires fresh
destinations rather than overwriting an older runtime:

```sh
just install-sdd .cache/sdd-review
just install-sdd .cache/sdd-review-app-common config/sdd-runtime-app-common
AUTOHUB_TEST_SDD_APP_COMMON="$PWD/.cache/sdd-review-app-common" just test-sdd .cache/sdd-review
AUTOHUB_TEST_SDD_APP_COMMON="$PWD/.cache/sdd-review-app-common" just test-sdd-pg .cache/sdd-review
```

Provisioning needs read access to the pinned sources. PostgreSQL contracts need
Docker/testcontainers; native CLI tests also require supported OS isolation.
The dedicated recipes fail when the runtime/isolation boundary cannot run.
They do not silently turn missing prerequisites into a passing CLI contract.
Serving-host installation and live verification belong in
[SDD runtime operations](../operations/sdd-runtime.md).

## SDK host and bridge fixtures

Run the owning flow integration path with SQLite or PostgreSQL:

```sh
just test modules/hub/tests/integration/features/execution/flows
just test-pg modules/hub/tests/integration/features/execution/flows
```

For disposable PostgreSQL without Docker, `AUTOHUB_FLOW_TEST_POSTGRES_URL` accepts
a `postgresql+psycopg` URL whose host is `127.0.0.1` and whose database name starts
with `autohub_test_`. Fixtures create/drop model tables; use a dedicated test DB.
Local worker HTTP tests bind loopback ports.

The optional two-application test reads `PLANHUB_APPLICATION_TEST_ROOT` and
`PLANHUB_APPLICATION_TEST_PYTHON` (an installed Python 3.13+ interpreter).
Without them the optional case is skipped. It launches loopback apps with isolated
state and planhub's installed SDK. Git/devkit are real; GitHub and PR-owner
completion are fixtures. It does not establish live CI/merge or production rollout.

## CI configuration

[.github/workflows/ci.yml](../../.github/workflows/ci.yml) declares
`workflow_dispatch`; it does not declare PR/push triggers. Its jobs call the
same root recipes after preparing their environments:

| Job | Checks |
| --- | --- |
| `backend` | Backend lint/types/SQLite and standalone SDK lint/types/tests/build |
| `backend-postgres` | PostgreSQL tests, migration upgrade/check and one-step downgrade/upgrade |
| `sdd-contract` | Pin consistency, both locked profiles, OS-isolated SQLite/PostgreSQL contracts |
| `frontend` | UI lint/types/build/tests and generated API freshness |

The SDD job requires `SDD_READ_TOKEN` for reviewed runtime source access. Execute
secret-backed checks only from a trusted reviewed branch; never expose those
credentials through untrusted PR execution. A local pass does not establish a CI
run or equivalence of secrets, operating-system isolation and PostgreSQL coverage.
