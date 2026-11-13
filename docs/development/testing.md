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

## Contributor command regressions

`modules/hub/tests/unit/scripts/test_frontend_workflow.py` executes the configured
setup, just recipes and npm script shell composition with isolated tool shims.
It covers locked Python/assets setup, frontend installation, fixing versus
read-only lint, module aliases and phase failures. Run it through the backend
recipe:

```sh
PYTEST_WORKERS=0 just test modules/hub/tests/unit/scripts/test_frontend_workflow.py
```

These fixtures verify command wiring without installing dependencies or creating
Git worktrees. A real `just init`, `just lint` and `just check` verify the installed
contributor environment separately.

## Repository activity and retirement contracts

Run the owning SDD activity/API, ordinary PR question/progression and migration
paths with the standard backend recipes. These tests verify optimistic dispatch,
exact claim recovery, history and permanent refusal of legacy execution; they do
not provision another repository's devkit runtime. PostgreSQL concurrency cases
still require PostgreSQL coverage.

## SDK host and retired bridge fixtures

Run the owning flow integration path with SQLite or PostgreSQL:

```sh
just test modules/hub/tests/integration/features/execution/flows
just test-pg modules/hub/tests/integration/features/execution/flows
```

For disposable PostgreSQL without Docker, `AUTOHUB_FLOW_TEST_POSTGRES_URL` accepts
a `postgresql+psycopg` URL whose host is `127.0.0.1` and whose database name starts
with `autohub_test_`. Fixtures create/drop model tables; use a dedicated test DB.
Local worker HTTP tests bind loopback ports.

Bridge tests cover deterministic retirement and receipt-backed observe-only
recovery. They do not require a local repository checkout or devkit seed runtime.
Generic flow/HTTP worker tests use their own controlled fixtures and do not
establish deployed worker cooperation or live CI/merge.

## Static CI references

`just check-ci-references` reads `.github/workflows/*.yml` and `*.yaml` run steps
without executing their commands. Backend lint invokes the same check, so the
default `just lint-check` and `just lint` catch missing directly named just recipes
or literal `config/` and `./config/` path arguments. Recipe and alias names come
from the root justfile through `just --dump`. A path may be quoted or assigned to
an option, such as `--manifest=config/example`; it resolves relative to the step,
job-default or workflow-default literal working directory, then repository root.
Failures identify the workflow, job and step and return exit 1.

The checker supports simple direct command lines and backslash continuations.
It ignores comments, display-only echo/printf commands and YAML prose fields.
Computed words, just options, shell assignments, compound commands, control-flow
blocks, functions/grouping, heredocs and directory-changing shell blocks are unsupported skips;
multiline compound continuations skip the whole run block. Dynamic working directories also skip their step. The printed skipped count is
unverified coverage, not a passed reference check. Nested scripts, variable
expansion, recipe argument schemas and external actions are not interpreted.
Invalid YAML, quoting or just introspection fails instead of passing silently.

`modules/hub/tests/unit/scripts/test_ci_references.py` runs disposable workflows
and justfiles. It verifies missing/existing recipes and aliases, deleted and
quoted paths, inherited directories, syntax boundaries and lint failure
propagation. A recipe side-effect sentinel confirms introspection does not run
recipes. Run these regressions with:

```sh
PYTEST_WORKERS=0 just test modules/hub/tests/unit/scripts/test_ci_references.py
```

## CI configuration

[.github/workflows/ci.yml](../../.github/workflows/ci.yml) declares
`workflow_dispatch`; it does not declare PR/push triggers. Its jobs call the
same root recipes after preparing their environments:

| Job | Checks |
| --- | --- |
| `backend` | Backend lint/types/SQLite and standalone SDK lint/types/tests/build |
| `backend-postgres` | PostgreSQL tests, migration upgrade/check and one-step downgrade/upgrade |
| `frontend` | UI lint/types/build/tests and generated API freshness |

No evaluator-install job or SDD source-read credential is required. A local pass
does not establish a remote CI run or PostgreSQL coverage.
