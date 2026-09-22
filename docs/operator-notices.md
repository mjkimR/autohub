# Operator Notices

Auto Hub stops and waits for its operator by design: a run pauses, is blocked, or fails, and nothing moves until
someone acts. Notices are how the hub reaches that person. They are a side effect of other work and never fail it.

## Notification channels

A notification channel is a place the hub can reach the operator. It is its own settings object, separate from
connectors: a connector authenticates the hub *to* a provider it works with, a channel only carries messages *out*.

- Managed under **Settings → Notifications** or `/api/v1/notification-channels` (list, create, patch, delete, and
  `POST /{id}/test`).
- The only kind today is `telegram`: the destination `chat_id` is stored as plain configuration, the bot token is
  sealed with the same AES-GCM key as connector credentials (bound to the channel, so a sealed token can never be
  replayed as a connector credential) and is never returned by the API.
- Every enabled channel receives notices at or above its configured minimum level (`min_level`: `debug`, `info`,
  `warning`, `error`, `critical`). The default is `info`. A test goes to the one named channel even when it is
  disabled, regardless of minimum level.
- Each channel records `last_sent_at` and `last_error`; a delivery that succeeds clears the error.

### Telegram setup

1. In Telegram, message `@BotFather`, send `/newbot`, and copy the bot token.
2. Send any message to the new bot, so it is allowed to write to you.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `result[].message.chat.id`.
   A group chat works too: add the bot to the group, post a message, and use the (negative) group chat id.
4. Add the channel in **Settings → Notifications**, pick its minimum notification level, and press **Send test**.

## What is announced

Housekeeping runs on every dispatcher tick (`POST /api/v1/dispatchers/trigger`), around the schedules the tick
executes. Each step logs its own failure and never fails the tick. Every outgoing message is tagged with its level
(e.g., `🚨 [ERROR]`, `⚠️ [WARNING]`, `ℹ️ [INFO]`).

| Notice | Level | When |
| --- | --- | --- |
| Run stopped | `error` | A pipeline run is `paused`, `blocked`, or `failed` at a revision nobody was told about. The notice names the repository, pull request, and pause reason. |
| Run waiting | `warning` | An in-flight run awaits draft-to-ready approval, a rejected connector token, or an external repository rule (compatibility only). See [Architecture](architecture.md#github-failures). |
| Trigger resumed | `info` | A tick arrives more than 10 minutes after the previous one. |
| Trigger stopped | `warning` | A GitHub webhook arrives while the last tick is more than 10 minutes old; at most once per hour. |
| Login lockout | `warning` | A caller failed to sign in five times within a minute and is locked out for five minutes. See [Development & Operations](development.md). |
| `@auto-run` lost | `error` | A replayed `@auto-run` delivery failed again (see below). |
| Channel test | `info` | A test notice sent manually via the dashboard or API. |

A stopped run is marked announced (`pipeline_runs.notified_revision`) only when at least one channel accepted the
notice, so a stop that could not be delivered is retried by the next tick and a channel added later still hears of
it. Stops older than 24 hours are not announced, and runs that existed before the migration count as announced.

## Scheduler trigger heartbeat

The hub does nothing on a timer by itself: an external trigger (Cloud Scheduler) must call the dispatcher. Each
tick records `last_tick_at` in the `dispatcher.heartbeat` system config. `GET /api/health/deep` reports it as
`last_tick_at` and `scheduler` (`ok`, `stale` after 10 minutes without a tick, `never`), and the dashboard shows
the same as **Scheduler Trigger**. With Cloud Run scaled to zero the hub cannot notice a stopped trigger on its
own; it notices when a webhook arrives, when the trigger resumes, or when someone opens the dashboard.

## Webhook delivery replay

A webhook is acknowledged before it is processed, and processing runs in the background of an instance that may
be stopped or throttled once the response is sent. GitHub's redelivery is rejected as a duplicate, and while
polling recovers a missed advance, nothing else would ever enroll a missed `@auto-run`.

Each delivery therefore keeps the few facts processing needs (`pull_number`, `auto_run`, `requested_catalog`)
instead of the payload, and the tick replays:

- a delivery still `received` two minutes after it arrived, and
- a `failed` delivery that carried an `@auto-run`,

once each (`attempts` is capped at two) and only within 24 hours. A replay claims the delivery first (`retrying`),
so two ticks never replay the same one. Enrollment and advance are already safe to repeat: enrollment is unique per
active pull request and advance runs under the run lease.

## History retention

The same tick housekeeping deletes history that only grows, at most once an hour:

| Table | Kept |
| --- | --- |
| `schedule_jobs`, succeeded | 7 days. A per-minute dispatch schedule writes about 1,400 rows a day per project, nearly all alike. |
| `schedule_jobs`, anything else | 30 days, for debugging. Retries happen within minutes, long before this. |
| `github_webhook_deliveries` | 90 days. The rows are also the deduplication keys; GitHub redelivers within days. |

Pipeline runs, their attempts, and AI catalog sessions are kept: they are the product's record and grow with real
work, not with the clock. The dispatch ledger has its own 30-day rule (see [AI Catalog Gateway](ai-catalogs.md)).

## Looking into what happened

- **Webhook deliveries** (Operations → Webhook deliveries, `GET /api/v1/github-webhook-deliveries`): what GitHub
  sent and what came of it, including why an `@auto-run` did not enroll or dispatch and whether a delivery was
  replayed. `noteworthy=true` (the UI default) keeps triggers and anything that failed or left a note; `status` and
  `repository` narrow further. Payloads are never kept.
- **Run detail** (Pipeline runs → attempt history): a summary of what the run has cost (requests posted to an
  agent, attempts by kind, usage-limit replies, elapsed time; `summary` on
  `GET /api/v1/pipeline-runs/{id}/attempts`) and, per attempt, its requests and the agent's replies in order.
- **Failed jobs**: a schedule job keeps the failure message when the error was written for an operator
  (application errors and sanitized GitHub errors), beside the request id. Anything else still only names the
  request id, and the stack trace stays in the logs.
- **Logs**: every pipeline run state change is logged from one place (`pipeline_runs/transition_log.py`) as
  `run <id> <repo>#<n>: <from> -> <to> (revision N) reason: …`. Use the application logger
  (`app_layer_base.core.log`): records sent to the standard `logging` module are not routed to the log sink, and
  anything below WARNING is dropped.
