# Delivery Status

Auto Hub is implemented and deployed. This document records the current
delivery state; the durable `@codex` request contract lives in
[Codex PR Mention Protocol](codex-pr-mention.md).

## Delivered

- GitHub CI observation, saved project connections, and project onboarding.
- PR enrollment, durable run/attempt/delivery history, leases, idempotency,
  mention reconciliation, watchdog retries, CI fixes, merge, and cancellation.
- HMAC-verified GitHub webhooks with delivery deduplication and polling
  recovery, plus parallel runs for different PRs in the same project.
- AI catalog gateway with per-kind quota policies (Codex usage windows, daily
  task caps), a dispatch ledger, pluggable pipeline execution adapters,
  project-level catalog selection, and scheduled Jules sessions
  (`jules.session`, `jules.sync_sessions`) with a session list. See
  [AI Catalog Gateway](ai-catalogs.md). Committed on 2026-09-15; not yet
  deployed.
- Jules session work types (2026-09-16): a `task` session's pull request is
  adopted into the project's pipeline as an already implemented run
  (`awaiting_ci` onward, CI fixes through the project's catalog); a `report`
  session's final message is stored on the session. Pull requests can also be
  enrolled as already implemented by hand. Verified against a mocked Jules
  transport only.
- Catalog designation (2026-09-16): `@auto-run:<catalog key or kind>` and the
  `catalog` field of manual enrollment pick the catalog for a run; the project
  selection stays the default and the seeded Codex catalog the fallback. A
  designated catalog is remembered on the run across resumes. Refused webhook
  triggers record their reason on the webhook delivery.
- Project agent schedules (2026-09-16): a project owns its recurring agent
  sessions; each row derives and owns one scheduler entry, the per-catalog
  session sync entry is kept automatically, and the generic schedule API
  refuses to edit owned entries. UI under Projects → Agent Schedules.
- Session list filters and ledger pruning (2026-09-21): the catalog session list
  filters by `status` (`open`, `completed`, `failed`) and `schedule_config_id`,
  with the status filter in the UI; admitting work prunes expired dispatch
  ledger rows of every catalog, not only the admitting one. Not yet deployed.
- Operator notices (2026-09-21): notification channels (Telegram) as their own
  settings object with a test send; stopped runs, a silent or resumed scheduler
  trigger, and unhandled `@auto-run` triggers are announced; the trigger
  heartbeat is reported by `/api/health/deep` and the dashboard; webhook
  deliveries whose processing was lost are replayed by the next tick. See
  [Operator Notices](operator-notices.md). Verified against a mocked Telegram
  transport only. Not yet deployed.
- `just setup-secrets` keeps existing bundle values on a re-run (2026-09-21)
  instead of regenerating the connector credential key and webhook secret.
- No Linear integration: Hub is the single source of truth for run state. A
  `linear` connector provider exists only so the connectors UI can store one.

## Verification

On 2026-09-14, a live canary on `mjkimR/test-sandbox` against Cloud Run and
Aiven PostgreSQL enrolled PRs, posted one `@codex` request, received a Codex
push, observed passing Actions CI, and completed the merge.

Local verification on 2026-09-15 (AI catalog generalization):

- Backend: 431 tests passing on SQLite and on PostgreSQL (testcontainers).
- Migrations: the full Alembic chain upgrades, downgrades, and re-upgrades on
  PostgreSQL 16. `alembic check` reports only two pre-existing column-comment
  differences (`pipeline_runs.pull_snapshot`, `schedule_configs.next_run_at`).
- Frontend: 8 component tests, `svelte-check`, production build, and lint
  passing.
- Jules was exercised only against a mocked HTTP transport; no live Jules or
  post-refactor Codex canary has run.

Local verification on 2026-09-16 (Jules work types): 442 backend tests on
SQLite, the Alembic chain upgrades, downgrades one step, and re-upgrades on
PostgreSQL 16 with `alembic check` reporting only the two pre-existing
column-comment differences, and 8 frontend tests, `svelte-check`, and lint
passing.

Local verification on 2026-09-21 (session filters, ledger pruning, type fixes):
479 backend tests on SQLite, 14 frontend tests, pyright, `svelte-check`, and
lint passing. After the operator notices work the same day: 489 backend tests
on SQLite and on PostgreSQL (testcontainers), 16 frontend tests, pyright, `svelte-check`, and lint passing; the
Alembic chain upgrades, downgrades one step, and re-upgrades on PostgreSQL 16
and `alembic check` reports no differences (the two column-comment differences
noted above are set by migration `061a3a930c1e`).

The automated suite covers crash recovery around delivery and head changes,
marker reconciliation, watchdog tolerance edges, webhook routing and polling
recovery, lease takeover, catalog admission and ledger counting, Jules session
creation, rate limiting, and reconciliation, and UI enrollment, pause, and
catalog policy editing.

## Follow-up canaries

- Add a Telegram channel in production, send a test, and confirm a paused run
  is announced.
- Re-run the Codex PR canary after deploying the refactored gateway.
- Run one live Jules session of each work type: confirm the v1alpha field
  names (`outputs[].pullRequest.url`, `agentMessaged.message`), that a task
  session's pull request is adopted and merged, the error returned at the
  daily and concurrent caps, and whether a limit is reported as HTTP 429.
- In a sandbox, enroll two PRs at once to validate production scheduler
  concurrency and duplicate enrollment handling.
- If webhook delivery reliability becomes a concern, validate a deliberately
  missed delivery recovering on the next scheduler poll.
- When onboarding a second repository, decide whether repository-specific
  branching policy is necessary.

## Explicitly deferred

- Automatic planning/WBS generation and dynamic agent selection.
- Automatic catalog routing (designation is explicit for now), Jules pushes
  to existing pull request branches, reports kept in git history, a hub ingest
  endpoint for agents, and richer quota history. Open items are tracked in the
  [AI Catalog Implementation Notes](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work).
- A bounded LLM review lane before merge.
