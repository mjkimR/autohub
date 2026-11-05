# Operator notices and diagnosis

Use this guide to configure a destination and investigate work that needs operator
attention. `CAP-NOTIFY-operator-notifications` owns channel and notice behavior;
`CAP-EXEC-scheduling-maintenance` owns schedule execution and retention.
`CAP-PR-webhook-advancement` owns signed intake and replay. These procedures do not
constitute fresh live verification or grant approval to advance development work.

## Configure Telegram

1. Create a bot through Telegram's `@BotFather` and retain its issued token.
2. Send the bot a message. For a group destination, add the bot and post there.
3. Read the destination's `message.chat.id` at
   `https://api.telegram.org/bot<TOKEN>/getUpdates`, substituting the issued token.
   A group chat commonly has a negative ID.
4. In **Settings → Notifications**, add the Telegram channel with its chat ID,
   token and desired minimum severity.
5. Press **Send test** and check the returned delivery result. A disabled channel
   can still be tested; enable it when it should receive broadcasts.

The equivalent configuration routes are `/api/v1/notification-channels`,
`PATCH /{channel_id}` and `POST /{channel_id}/test`. Read `last_error` after failure;
correct the destination or rotate the token through the patch route, then test
again. Public channel responses do not expose the stored token.

## Check whether the trigger is firing

Read `GET /api/health/deep` or **Scheduler Trigger** on the dashboard. Inspect
`scheduler` and `last_tick_at` before treating an idle run as an agent failure.
If the trigger is stale, inspect the Cloud Scheduler job, its machine credential
and recent HTTP results. Follow [scheduler provisioning](cloud-run-deployment.md#6-register-cloud-scheduler-periodic-trigger)
when repairing the job or rotating its key.

An internal 60-second schedule interval does not increase the external tick's
frequency. Trigger silence is observed through incoming traffic or a later tick;
an instance without traffic does not independently monitor itself.

## Diagnose a run or connection test

- Open the Run and inspect its state, pause reason, current revision and attempt
  history before deciding whether to answer, resume, repair credentials or wait.
  `GET /api/v1/pipeline-runs/{run_id}/attempts` exposes the attempt summary;
  delivery/reply views show request correlation and observed agent responses.
- Treat a connection test's result and cleanup status separately. Inspect its
  ownership evidence before any cleanup action. Use `CAP-CONN-connection-verification`
  for its state and recovery contract.
- Inspect **System maintenance** schedule jobs for shared cleanup/result collection.
  Stop individual work through its owner rather than disabling this shared worker.
- A successful scheduler job means its handler completed; it does not establish
  that a PR merged, an SDK flow completed or remote cleanup finished.

## Diagnose a missed webhook trigger

Open **Operations → Webhook deliveries** or query
`GET /api/v1/github-webhook-deliveries`. Filter by `repository`, `status` or
`noteworthy=true`; identify the delivery before repeating an enrollment request.
Read `failure_detail` to distinguish skipped enrollment, deferred first dispatch,
failed processing and an ordinary successful notification.

For queued processing, inspect Cloud Tasks callback HTTP results alongside the
stored delivery. Use [queue provisioning](cloud-run-deployment.md#61-webhook-processing-queue-cloud-tasks-recommended)
for queue/IAM settings. GitHub redelivery alone does not reprocess a delivery ID
already stored; the canonical webhook contract defines bounded scheduler replay.

## Logs and expired history

Correlate a failed job's request ID with the configured application log sink.
Safe operator-facing errors may be retained on the job; other exceptions require
server logs. PR transition records include the Run ID, repository/PR, state change,
revision and optional reason. Their visibility depends on the deployed log level.

Use `CAP-EXEC-scheduling-maintenance` for retention clocks and protections. An
expired Run no longer has local detail/resume history. Retained Work Item results,
provider reports and external PR URLs can outlive that Run; their survival does
not mean the remote work was newly verified. History pruning does not delete
remote GitHub branches or provider sessions.
