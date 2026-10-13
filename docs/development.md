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
The standalone pipeline SDK lives in `packages/sdk`. `just init sdk` prepares the
Python workspace, `just lint sdk` and `just check sdk` check it, and `just test-sdk`
and `just build-sdk` test and package it. Default lint/check include the SDK;
`just test` remains the backend suite. See the [SDK README](../packages/sdk/README.md).
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

검사 명령은 `devkit run`으로 출력량을 제한하며 전체 진단은 결과에 표시된 로그 경로에 저장한다. Initialize the backend with `just init hub` before running
these commands, including frontend-only checks. Use `just lint-check` for read-only
format/lint verification.

This repository does not install Git hooks. Run `just lint`, `just check`, and
the relevant tests before finishing changes, as required by `AGENTS.md`. CI uses
the same recipes and locked Python dependencies; Ruff has no separate hook version.

## Agent skills


app-common 개발 자산은 Python 의존성에 포함된 devkit bundle에서 설치한다.
`just skills`와 `just link-skills`는 설치된 패키지에서 `devkit sync`로 자산을 생성하고
Python advisory guide를 선택한다. `.devkit/`과 투영 스킬 디렉터리는 Git에서 무시한다.
새 환경마다 Python lock에서 설치한 패키지로 다시 생성하므로 receipt나 스킬을 커밋하지 않는다.
자체 Python SDK에는 backend 런타임 의존성을 추가하지 않는다.
프런트엔드 ESLint 정책은 독립 pin을 유지한다. sibling checkout이나 APM은 필요하지 않다.

의존성 갱신은 공개 커밋으로 수행한다:

```sh
uv run devkit app update --ref <pushed-commit>
uv run devkit sync --check
```

manifest와 uv.lock 변경을 함께 검토한다. 새 체크아웃과 CI는
`uv sync --locked --all-packages` 다음 `uv run --no-sync devkit sync`를 실행한다.
관리 파일이나 투영 파일을 직접 편집하지 않는다. devkit 개발 도구는 Linux/macOS를 지원한다.

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

[WorkPlan-linked runs](work-plans.md#history-retention) also require explicit Item
merge evidence at least 30 days old before pruning. Unresolved Item runs remain
protected, and durable Item results survive Run expiry. Shared maintenance also
publishes outbound WorkPlan/Item Issue records independently of execution.

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

- **Accounts** come from [`app-prebuilt-auth`](https://github.com/mjkimR/app-common/tree/main/packages/prebuilt/app-prebuilt-auth). Browser password login uses `POST /api/v1/auth/browser/login`, returning a short-lived access token and an HttpOnly `autohub_refresh` cookie; Google login uses the same cookie session. The UI keeps access tokens only in memory, restores them with `POST /api/v1/auth/browser/refresh` on page load, and retries once after a 401. Cookie/DB expiry slides by `REFRESH_TOKEN_EXPIRE_DAYS` (default 14; 7 in the deployment bundle). Password changes or account revocation prevent renewal. Explicit logout calls `/api/v1/auth/browser/logout` to revoke that browser session and notifies other tabs; previously issued access tokens retain their short lifetime. Only the email is remembered in localStorage. Old sessionStorage tokens are cleared, requiring one sign-in after upgrading. Apply the browser-session migration before deploying. Same-origin hosting/Vite proxy is supported by default; separate frontend origins require `BROWSER_AUTH_ALLOWED_ORIGINS` and exact credentialed CORS configuration. Production cookies use HTTPS. For shell clients, `/api/v1/users/login/` and `/api/v1/users/login/refresh` retain their JSON token contract: `just login-token --url https://YOUR_HUB_HOST --email you@example.com` prompts without echo and prints the access token (`--out FILE` writes a 600-mode file; `--json` includes the refresh token).
- **The operator's account** is created at startup from `FIRST_USER_EMAIL` / `FIRST_USER_PASSWORD`, and with `FIRST_USER_SYNC_PASSWORD=true` its password follows that setting on every start. The secret bundle therefore stays the one place a password is changed (`just update-password`). The database holds only an Argon2id hash: reading it does not let anyone sign in.
- **The scheduler uses a managed machine key.** Register a machine with the `autohub:dispatch` scope through `/api/v1/machines`, issue its key, and send it as `X-API-Key` to `POST /api/v1/dispatchers/trigger`. Revoked/expired keys and inactive machines are rejected. The key opens no other workload route; a signed-in user can still trigger a tick from the UI. Legacy `SCHEDULER_KEY` / `X-Scheduler-Key` is no longer accepted.
- **Machine management** accepts a signed-in human administrator or `X-Root-API-Key` matching the optional `APP_API_KEY_ROOT_KEY` deployment setting. Root manages machines/keys only, cannot sign in, and cannot trigger work or manage users. Root is not stored in the DB; rotate/remove it in deployment settings and restart every instance. See [deployment](cloud-run-deployment.md) for initial provisioning and key rotation.
- **Guessing is held off by a lockout**: five failed logins within a minute lock the caller out for five minutes (HTTP 429 with `Retry-After`), even with the right password, and the operator is told through [Operator Notices](operator-notices.md) with a partly masked address. The caller is the address Cloud Run appends to `X-Forwarded-For`, so invented forwarded addresses do not dodge it. Counters are per process, so several workers multiply the attempts a caller gets; that is still a handful per minute.
- The GitHub webhook endpoint is outside all of this: GitHub signs it with the webhook secret. Its Cloud Tasks callback carries an expiring HMAC derived from the same secret; see [deployment](cloud-run-deployment.md#61-webhook-processing-queue-cloud-tasks-recommended).

## Runtime Environment

The baseline deployment model hosts the backend on Cloud Run, with Cloud Scheduler triggering `POST /api/v1/dispatchers/trigger`. This does not imply full deployment automation is complete.
Currently, HTTP trigger responses return after tasks for that tick finish executing.
Align timeouts across the application, Cloud Run, and Cloud Scheduler; pipeline observation tasks must complete inspection and persistence within their own bounded timeout and exit cleanly.

## Testing

External GitHub calls are isolated by swapping the HTTP transport, while DB persistence is verified against real test databases.
Complex pure CI evaluation logic is verified through unit tests, while API/schedule/report integration is verified through integration and E2E tests.
For fixtures and conventions, consult the app-common testing guide: `.agents/skills/app-common/references/testing/index.md` after `just skills`, or `uv run devkit app guide show testing`.

## Continuous Integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`. It only prepares the runtimes (uv,
Node from `.nvmrc`, `just`) and calls the `justfile` recipes, so a check that passes locally passes there.

| Job | What it runs |
| --- | --- |
| `backend` | `just lint-check hub` (ruff format and lint, architecture checks), `just check hub` (pyright), `just test` (SQLite) |
| `backend-postgres` | `just test-pg` (testcontainers), then against a PostgreSQL 16 service: `alembic upgrade head`, `alembic check` (the migrations match the models), one step down and up again |
| `specrig-contract (release)` / `specrig-contract (layered)` | Pinned released CLI and pinned upcoming layered source: `just test-specrig`; missing CLI is a failure |
| `frontend` | `just lint-check hub-ui`, `just check hub-ui` (`svelte-check` and the production build), `just test-ui`, and `just check-ui-api`: stale or missing tag-based API declarations fail the build |

The job names are stable, so this repository can itself be enrolled in a hub project with `ci.yml` as the workflow
and the backend/frontend jobs plus both specrig contract jobs as required checks. The
specrig jobs require `SPECRIG_READ_TOKEN` with read access to the private specrig
repository and release assets. They fail when the runtime cannot be provisioned;
they never silently skip the CLI contract. Fork PRs do not receive this secret;
run these checks from a trusted branch after review, never via `pull_request_target`
with untrusted PR code. Other jobs need no repository secret: OpenAPI export works
without environment configuration and app-common is public and pinned by commit.

## Test selection

See [the test guide](../modules/hub/tests/README.md) for source-mirroring paths and
unit/integration/e2e boundaries. `just test-unit` runs isolated logic;
`just test-integration` runs real DB and in-process API contracts.
`just test` retains all backend coverage.


## SDK flow host

Apply migration `d69f762c5465` with the matching backend. The backend depends on
`autohub-sdk` through the UV workspace; the backend Docker build includes its source.
SDK releases are immutable definitions, not executable uploads. Native bindings
accept only `autohub.identity`, a pure input echo for contract verification.

Provision a managed machine with `autohub:task:write` and `autohub:task:read` for
catalog registration, activation, submission and polling. Approval/rework commands
also require `autohub:task:approve`. The first machine registering a provider/environment
owns it across key rotations. `autohub:dispatch` alone grants no flow API access.
See the [wire contract](sdk-task-flow.md) for SDK endpoints.

Configure HTTP workers using the server environment, for example:

```sh
AUTOHUB_FLOW_HTTP_TARGETS='{"planhub-worker":{"base_url":"https://worker.example","credential_env":"PLANHUB_WORKER_KEY"}}'
```

A release binding uses executor `http` and target `planhub-worker`. HTTPS is required
except for loopback HTTP. URLs cannot contain credentials, query strings or fragments.
Resolved target URLs and credential environment variable names are pinned in the
release/run snapshot; changing target configuration requires a new release. Rotate
credential values independently. Secrets are not accepted in release definitions.
Workers must validate task contract and release identity/digest before execution.

Workers implement this protocol relative to `base_url`:

| Operation | Request | Response |
| --- | --- | --- |
| Submit | `POST /executions`, JSON `attempt_id`, `run_id`, `task`, `inputs`, `release_id`, `release_digest` | Accepted `pending` or terminal result |
| Inspect | `GET /executions/{attempt_id}` | Current result, or typed authoritative `not_found` |
| Cancel | `DELETE /executions/{attempt_id}` | `pending` until stopped, then a terminal result |

Every request includes `Idempotency-Key: <attempt UUID>` and, if configured,
`X-API-Key` from the referenced environment variable. Responses contain
`attempt_id`, status (`pending`, `completed`, `failed`, `canceled`, `not_found`),
optional `output` object and `error`. Completed results require output. A 404 is
accepted as absence only for inspection and only with the matching typed
`not_found` response. Redirects are disabled and calls have a five-second timeout.

The worker must persist idempotent attempt receipts and cancellation tombstones:
a cancellation of an unknown ID must fence a later submit of the same ID. A
plain 404 from DELETE is not cancellation evidence. Terminal completion/failure
can acknowledge cancellation while preserving evidence of an already finished
external effect; host cancellation does not roll that effect back. This protocol
requires cooperation from the worker and does not guarantee exactly-once effects.

`System maintenance` advances up to 32 ready runs, one action per run per tick.
It commits dispatch intent before I/O and fences result writes with a 60-second
lease and run revision. Unknown results reconcile the same attempt instead of
starting a new one. Polling is eligible after five seconds, but production's
five-minute dispatcher tick determines actual latency. POST/GET run APIs never
advance workers themselves. Approval expiry is checked on commands and persisted
on the next maintenance advance. SDK flow records have no automatic retention yet.

Run `just test modules/hub/tests/integration/features/execution/flows` for API,
recovery and real SDK HTTP tests; `just test-pg` with the same path also verifies
PostgreSQL contention. For a disposable local PostgreSQL without Docker, set
`AUTOHUB_FLOW_TEST_POSTGRES_URL` to a `postgresql+psycopg` URL whose host is
`127.0.0.1` and database name starts with `autohub_test_`. Test fixtures create and
drop model tables, so use a dedicated test database. Run `just gen-ui-api` after
wire/API changes. The native specrig/PR bridge has an additional domain approval contract; generic
machine approval alone is not PR approval evidence.

## Native specrig runtime

Native project mode accepts an existing PR and a bound spec. Select the spec in
**Repository**, check readiness against the PR head, then start execution. The
spec's recent executions link directly to **Runs → Decisions**, where the latest
final-report, review and reverify envelope summaries are tied to the inspected
commit. Work Plans do not yet create native specrig specs or PRs.

`config/specrig-release.json` pins the production version, commit and platform
archive checksums. The current pin is **0.1.2** (legacy harness layout). Layered
support is tested against `compatibility_commit`, an upcoming source commit built
as a test-only `0.0.0` fixture. It is not shipped as a production release. After a
layered release is published, review its assets and update the version, commit and
all checksums together, provision a fresh runtime, and run both contract checks.
Do not substitute a sibling checkout binary or silently track `latest`.

```sh
# gh must have read access to the private release assets.
just install-specrig
export AUTOHUB_SPECRIG_HOME="$(pwd)/.cache/specrig"
export PATH="$AUTOHUB_SPECRIG_HOME/bin:$PATH"
just test-specrig
```

The installer verifies the reviewed checksum and CLI identity, then lets specrig
create its official offline release cache. The server reads `pin.json` from
`AUTOHUB_SPECRIG_HOME` (default `/opt/specrig`). `AUTOHUB_SPECRIG_VERSION` can
explicitly override the full identity string for tests/managed runtimes; it does
not install a binary or upgrade an enrolled run.

Each inspection fetches exact head/base commits into a disposable checkout. A
release installation receipt must match the server's repository, version and
commit. Hub runs `installation restore --offline` from the provisioned cache
before inspecting a layered harness. Missing caches, unsupported local layered
receipts and version mismatches fail readiness; Hub never initializes, upgrades
or rewrites the project's recorded installation. Legacy tracked harnesses without
a release receipt remain supported. No additional persistent checkout is needed.

Native evaluation supports bundled rules only. The CLI receives Git and specrig
on a restricted PATH, a private temporary directory and locale; it does not
inherit connector/server credentials or Go. Repository runner caches are removed
from the disposable checkout. Custom Go rules need a separate trusted runner;
they are reported as runtime/setup errors rather than agent repair work. Only
`RULE_VIOLATIONS_DETECTED` is a final-lint repair result. Safe CLI diagnostic codes
and bounded rule identifiers are exposed; raw stderr is not returned to clients.

The Hub Dockerfile includes Git, the pinned CLI and offline cache. For private
assets, local builds accept `GH_TOKEN` through a BuildKit secret, and Cloud Build
accepts `SPECRIG_BUILD_SECRET=<Secret Manager secret name>` (same GCP project).
Grant its build service account secret access before deploying. The secret is
mounted only during provisioning, never copied to the runtime. A missing private
release credential fails the image build. The resulting image contains specrig's
binary and harness assets; distribute it according to that repository's access
policy. The SDK's optional mounted-checkout bridge below remains separately
configured.

### Live canary after deployment

Use a designated test repository and PR with the matching release receipt and
bound workflow. This is an external-write test and must use an approved target.

1. Check readiness, start the native run, and follow its link from the spec view.
2. Reach a draft human gate; verify the wait releases its execution slot and the
   Decisions dialog links report evidence to the actual inspected commit.
3. Exercise a provider question, save an answer, then explicitly resume with it.
   Verify the next request contains that selected answer without implied approval.
4. Approve integration, revoke before progression, and confirm no merge. Request
   changes and verify a changed head requires renewed evidence/approval.
5. Explicitly approve the final evidence, mark the test PR ready, then confirm the
   configured CI checks and merge policy complete that same PR exactly once.
6. Keep run/PR links and the approval history as canary evidence. Local mock tests
   do not establish provider question behavior, GitHub protection or live delivery.

### SDK flow bridge with an existing PR

Configure server-owned targets before registering the planhub release:

```sh
AUTOHUB_FLOW_DELIVERY_TARGETS='{"local":{"provider":"planhub","environment":"local","project_id":"<existing-project-uuid>","checkout":"/absolute/clean/checkout"}}'
```

This allows `autohub.specrig:local` and `autohub.pr_delivery:local` only in that
provider/environment. Provision Git and the specrig CLI on the server PATH and
mount a clean checkout whose HEAD matches the reviewed PR. Release registration
does not deploy worker code or checkout files. The Hub image packages Git and
the native pinned CLI/cache above; a bridge checkout still needs explicit provisioning. Apply migration `e70a873d6576`
for durable PR claims and approval evidence.

The initial flow accepts an existing paused PipelineRun whose latest attempt was
implemented externally. It verifies review/reconcile/final-report through the real
CLI, then requires a scoped approve command before resuming the same PR owner.
Approval records the machine/key actor and evidence digest. GitHub head and PR
revision are rechecked at resume; retries reuse the existing resume receipt.
The operator still controls PR ready, while the existing owner handles CI/merge.
A failed delivery attempt cannot be automatically retried under a different PR
owner; resolve the existing PR state explicitly. Cancellation fences future
resume and stops the PR controller, without rolling back posted agent requests.

For the optional two-application HTTP test, set
`PLANHUB_APPLICATION_TEST_ROOT` to the planhub checkout and
`PLANHUB_APPLICATION_TEST_PYTHON` to its installed Python 3.13+ interpreter, then
run the flow test path. The test launches loopback applications with isolated
state and uses planhub's installed SDK. Git/specrig are real; GitHub and PR owner
completion are fixtures. Live CI/merge and production rollout remain separate.
