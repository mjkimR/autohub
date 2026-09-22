# Development & Operations

## Commands

Refer to the [justfile](../justfile) for actual targets, aliases, defaults, and implementations.

```sh
just init
just dev-run hub
just dev-run hub-ui
just lint
just check
just test
just test-ui
just gen-ui-api
```

`just lint` automatically fixes Python formatting and lints.
`just check` runs Python type checking and the Frontend production build.
Default tests use SQLite; `just test-pg` uses PostgreSQL testcontainers and needs a running Docker daemon.
`just test-ui` runs the frontend component test suite.
Vitest keeps transformed modules on disk between runs; every test still executes.
To compare without the transform cache, run
`npm --prefix modules/hub-ui test -- --fsModuleCache=false` with the repository's Node version.
When API definitions change, run `just gen-ui-api` to regenerate the client SDK.
Frontend commands activate the Node version in `.nvmrc` through nvm; if that version is not installed, `nvm use` fails and `just gen-ui-api` exits with status 3 without further output.
The Frontend strictly consumes the generated SDK.

Frontend lint includes the shared app-common file-size policy: Svelte components
allow 500 counted lines, TypeScript 400, and routes 200. Blank lines and JS/TS
comment-only lines are excluded; markup, styles, and HTML/CSS comments count.
Generated shadcn primitives, tests, and declarations are excluded. An overage is
an error: split a cohesive component/helper out, or record an exact-file exception
with a reason and finite ceiling in `modules/hub-ui/eslint.config.js`. Do not turn
off the rule or automatically raise ceilings. See the installed app-common
`ui/structure` guide after `just skills`. CI enforces the same policy through
`just lint-check hub-ui`.

Checks use `app-tools run` for compact output; complete diagnostics are saved at
its printed `log:` path. Initialize the backend with `just init hub` before running
these commands, including frontend-only checks. Use `just lint-check` for read-only
format/lint verification.

This repository does not install Git hooks. Run `just lint`, `just check`, and
the relevant tests before finishing changes, as required by `AGENTS.md`. CI uses
the same recipes and locked Python dependencies; Ruff has no separate hook version.

## Agent skills


Microsoft APM 0.30.0 installs the `app-common` skill with `just skills` (also run
by backend initialization). `just link-skills` remains a compatibility entry point.
`apm.yml` pins the Git dependency to the same pushed commit as the shared frontend
ESLint policy. Python runtime packages retain their independently pinned commit;
no sibling app-common checkout is required. Install APM with
`uv tool install apm-cli==0.30.0`. Private repositories require Git credentials in
local and cloud agent environments.

Normal setup runs `apm install --frozen`. To adopt a newer skill version, change
`ref` in `apm.yml` to the intended pushed commit, then run:

```sh
apm install --refresh
apm audit --ci
```

From workbench, `just skills-refresh autohub` performs both steps. Refresh honors
the declared ref; it does not advance a pinned commit to main automatically.
Track `apm.yml`, `apm.lock.yaml`, and the deployed skill files together. Ignore
`apm_modules/`; never edit installed copies. This setup does not use a project
`.apm/` directory. Keep the skill ref aligned when updating app-common packages.

## Existing Scheduler Foundation

The backend follows the `API → UseCase → Service → Repository` clean architecture flow.
Tasks are registered with `@task(name="namespace.name")` and Pydantic payloads.
Domain packages must be imported in `app/features/execution/tasks/domains/__init__.py` for auto-discovery.
Task schemas can be inspected via `/api/v1/tasks/specs`.

`ScheduleConfig` stores cron or interval configuration alongside the payload.
The dispatcher claims due schedules inside a database transaction and records a `ScheduleJob`.
While PostgreSQL's `FOR UPDATE SKIP LOCKED` coordinates concurrent schedule selection, it does not solve external request deduplication, unexpected process termination, or tick overlaps on its own.

`ScheduleJob` records pending/success/failure states and timestamps.
Failure messages report the request ID; detailed exceptions remain in server logs.
Never log credentials or personally identifiable information (PII).
Even if the pipeline CI fails, if the observation query itself succeeds, the `ScheduleJob` is marked as success.
CI status and failure rationales are inspected via the observation report.

## System maintenance

The installation owns exactly one **System maintenance** schedule (`system.maintain`).
Migration `f4d5e6f7a8b9` seeds it; application startup and each dispatcher trigger
repair a missing or disabled entry without resetting a healthy schedule's due time.
A fixed ID and a partial unique task index prevent duplicate system schedules.
The generic schedule API rejects creating, editing, pausing, repurposing, or deleting
this task (409); the UI labels it **System Managed** and offers no mutation controls.

It advances active connection tests, retries unfinished cleanup, and collects Jules
catalogs with unfinished sessions or completed task PRs awaiting adoption. It does
not create Jules sessions. Pending work remains eligible after a project or Agent
Schedule is disabled/deleted. Connector access is still required; individual
failures do not stop the other items and unresolved work is retried later.
Existing per-test leases arbitrate manual and scheduled test advances.

The worker also prunes history hourly: successful jobs after 3 days, failed jobs
after 7 days, and terminal pipeline runs after 30 days. Pending/retryable jobs and
active/paused/blocked runs survive. The `maintenance.history` checkpoint is locked
and committed with deletion; a failed pass retries on the next tick. Batches are
bounded to 1,000 jobs and 200 runs. See [retention details](operator-notices.md#history-retention).
Migration `a5e6f7a8b9c0` adds a session marker so removing old runs cannot cause Jules
PR re-adoption; session reports and PR links remain available.

The internal interval is 60 seconds, subject to the external dispatcher tick (five
minutes in production). Work uses bounded concurrency of four and the dispatcher's
overall execution timeout. When both connection tests and Jules catalogs have pending
work, each gets two workers; a single kind can use all four. The `maintenance.queue`
checkpoint records the last attempted item of each kind before external work starts.
Subsequent ticks resume after those cursors, including after cancellation or a restart,
so slow or failing items cannot keep the same items at the front of the queue.
Stop individual work through Connections or Agent Schedules; do not disable the
shared maintenance worker.

Upgrade removes hub-owned `pipeline.connection_test` schedules and catalog entries
named `Agent sync: <key>`, retaining domain records and job/session history. Historical
job links to removed configs become null. Operator-created sync entries and recurring
Agent Schedules remain unchanged. Rollback recreates workers for unfinished probes
and Jules catalogs with schedules/sessions. Deploy migrations with the matching app
version; old workers must not continue creating per-test schedules after upgrade.

## Database & Credentials

The production database is PostgreSQL, and migrations are managed with Alembic.
Refer to the `justfile` for `just db-upgrade` and `just db-revision` arguments.
GitHub credentials are stored encrypted in Connectors.
For encryption key configuration, follow the [Hub module documentation](../modules/hub/README.md#connector-credential-encryption).
People sign in; the scheduler holds a key of its own.

- **Accounts** come from [`app-prebuilt-auth`](https://github.com/mjkimR/app-common/tree/main/packages/prebuilt/app-prebuilt-auth). `POST /api/v1/users/login/` (an OAuth2 password form) answers with a 10-minute access token, sent as `Authorization: Bearer ...`, and a refresh token. `POST /api/v1/users/login/refresh` exchanges the refresh token for a new pair, so a session ends after `REFRESH_TOKEN_EXPIRE_DAYS` without use (7 in the deployment bundle), and at once when the password changes. The UI keeps only the two tokens, in `sessionStorage`, renews an expired access token once and repeats the request, and remembers the email between visits. The password exists in the sign-in form and nowhere else in the browser.
- **The operator's account** is created at startup from `FIRST_USER_EMAIL` / `FIRST_USER_PASSWORD`, and with `FIRST_USER_SYNC_PASSWORD=true` its password follows that setting on every start. The secret bundle therefore stays the one place a password is changed (`just update-password`). The database holds only an Argon2id hash: reading it does not let anyone sign in.
- **The scheduler uses a managed machine key.** Register a machine with the `autohub:dispatch` scope through `/api/v1/machines`, issue its key, and send it as `X-API-Key` to `POST /api/v1/dispatchers/trigger`. Revoked/expired keys and inactive machines are rejected. The key opens no other workload route; a signed-in user can still trigger a tick from the UI. Legacy `SCHEDULER_KEY` / `X-Scheduler-Key` is no longer accepted.
- **Machine management** accepts a signed-in human administrator or `X-Root-API-Key` matching the optional `APP_API_KEY_ROOT_KEY` deployment setting. Root manages machines/keys only, cannot sign in, and cannot trigger work or manage users. Root is not stored in the DB; rotate/remove it in deployment settings and restart every instance. See [deployment](cloud-run-deployment.md) for initial provisioning and key rotation.
- **Guessing is held off by a lockout**: five failed logins within a minute lock the caller out for five minutes (HTTP 429 with `Retry-After`), even with the right password, and the operator is told through [Operator Notices](operator-notices.md) with a partly masked address. The caller is the address Cloud Run appends to `X-Forwarded-For`, so invented forwarded addresses do not dodge it. Counters are per process, so several workers multiply the attempts a caller gets; that is still a handful per minute.
- The GitHub webhook endpoint is outside all of this: GitHub signs it with the webhook secret.

## Runtime Environment

The baseline deployment model hosts the backend on Cloud Run, with Cloud Scheduler triggering `POST /api/v1/dispatchers/trigger`. This does not imply full deployment automation is complete.
Currently, HTTP trigger responses return after tasks for that tick finish executing.
Align timeouts across the application, Cloud Run, and Cloud Scheduler; pipeline observation tasks must complete inspection and persistence within their own bounded timeout and exit cleanly.

## Testing

External GitHub calls are isolated by swapping the HTTP transport, while DB persistence is verified against real test databases.
Complex pure CI evaluation logic is verified through unit tests, while API/schedule/report integration is verified through integration and E2E tests.
For fixtures and conventions, consult the app-common testing guide: `.agents/skills/app-common/references/testing/index.md` after `just skills`, or `uv run app-tools guide show testing`.

## Continuous Integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`. It only prepares the runtimes (uv,
Node from `.nvmrc`, `just`) and calls the `justfile` recipes, so a check that passes locally passes there.

| Job | What it runs |
| --- | --- |
| `backend` | `just lint-check hub` (ruff format and lint, architecture checks), `just check hub` (pyright), `just test` (SQLite) |
| `backend-postgres` | `just test-pg` (testcontainers), then against a PostgreSQL 16 service: `alembic upgrade head`, `alembic check` (the migrations match the models), one step down and up again |
| `frontend` | `just lint-check hub-ui`, `just check hub-ui` (`svelte-check` and the production build), `just test-ui`, and `just gen-ui-api` followed by a diff: a stale `schema.d.ts` fails the build |

The job names are stable, so this repository can itself be enrolled in a hub project with `ci.yml` as the workflow
and these three jobs as the required jobs. Nothing needs a secret: the app imports and exports its OpenAPI schema
without any environment, the tests set their own, and `app-common` is a public repository pinned by commit.

## Test selection

See [the test guide](../modules/hub/tests/README.md) for source-mirroring paths and
unit/integration/e2e boundaries. `just test-unit` runs isolated logic;
`just test-integration` runs real DB and in-process API contracts.
`just test` retains all backend coverage.
