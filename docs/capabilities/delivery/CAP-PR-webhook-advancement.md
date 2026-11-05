---
id: CAP-PR-webhook-advancement
title: Signed webhook intake and recoverable advancement
summary: "Auto Hub authenticates GitHub deliveries, records minimal routing facts and advances or enrolls their PR work through recoverable processing. Queued callbacks and bounded scheduler replay preserve recovery without retaining raw payloads."
area: delivery
status: active
usecases:
  - UC-deliver-pull-request
entrypoints:
  - modules/hub/app/features/project_management/github_webhooks/api.py
  - modules/hub/app/features/project_management/github_webhooks/usecases.py
  - modules/hub/app/features/project_management/github_webhooks/tasks.py
---

# [CAP-PR-webhook-advancement] Signed webhook intake and recoverable advancement

## 1. Summary

GitHub events wake the existing PR execution owner or request enrollment through
`@auto-run`. Hub stores a delivery before queuing its processing and retains the
facts required for recovery. `CAP-PR-pull-request-delivery` owns enrollment,
advancement leases, provider effects and merge authority; a webhook acknowledgement
is not evidence that any of those operations completed.

## 2. Scope & Boundary

- **In-Scope**: body-signature admission, delivery-ID deduplication, minimal stored
  routing facts, Cloud Tasks callbacks, processing outcomes and stalled replay.
- **Out-of-Scope**: GitHub event delivery, Cloud Tasks availability and queue IAM
  belong to external services/operator setup. PR execution and Work Plan admission
  retain their domain owners. `CAP-NOTIFY-operator-notifications` owns notices.
- **Scope Excluded**: storing raw GitHub payloads, treating duplicate redelivery as
  a retry command and exactly-once remote execution under concurrent or uncertain I/O.

## 3. Business Rules & Policies

1. **Signed intake**: IF the webhook body's signature does not match the configured
   secret, THEN Hub MUST refuse intake with HTTP 401 before storing the delivery.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
   `test_github_webhook_rejects_invalid_signature`.
2. **Delivery identity**: WHEN a stored delivery ID arrives again, Hub MUST return
   HTTP 202 with `status: duplicate` without scheduling another processing pass
   through that intake request.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
   `test_github_webhook_verifies_signature_and_deduplicates`.
3. **Bounded public disclosure**: WHEN listing delivery history, Hub MUST expose
   routing/outcome facts rather than the payload digest or raw request body.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
   `test_the_delivery_log_lists_deliveries_and_finds_the_noteworthy_ones`.
4. **Queue selection**: WHEN the processing queue accepts a stored delivery, Hub
   MUST omit the in-process background processing pass for that intake request.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_webhook_tasks.py`,
   `test_a_queued_delivery_is_not_also_processed_in_the_background`.
5. **Fallback processing**: IF the queue is unset or does not accept a delivery,
   THEN Hub MUST schedule in-process background handling of that stored delivery.
   Checks: `modules/hub/tests/integration/features/project_management/github_webhooks/test_webhook_tasks.py`,
   `test_enqueue_reports_an_unset_or_refusing_queue`,
   `test_a_queued_delivery_is_not_also_processed_in_the_background`.
6. **Callback authority**: IF a queued callback lacks a matching unexpired
   signature bound to its delivery ID, THEN Hub MUST refuse it with HTTP 401.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_webhook_tasks.py`,
   `test_task_signature_is_bound_to_the_delivery_and_expires`,
   `test_the_callback_processes_a_stored_delivery_once`.
7. **Completed callback replay**: WHEN a callback repeats after its stored delivery
   left `received`, Hub MUST skip processing through that callback.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_webhook_tasks.py`,
   `test_the_callback_processes_a_stored_delivery_once`.
8. **Enrollment request**: WHERE trigger enrollment is enabled for an enabled
   matching project, WHEN a supported `@auto-run` event has no active PR owner,
   Hub MUST submit enrollment using its parsed optional catalog designation.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
   `test_webhook_pr_opened_with_auto_run_enrolls_and_advances`,
   `test_webhook_trigger_passes_the_named_catalog_to_enrollment`.
9. **Existing PR owner**: WHEN a delivery resolves to an existing active PR run,
   Hub MUST advance that owner instead of enrolling a replacement.
   Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
   `test_webhook_comment_with_auto_run_advances_existing_active_run`,
   `test_out_of_order_webhooks_route_each_pull_request_to_its_own_active_run`.
10. **Expected deferral**: WHEN enrollment or advancement raises a domain refusal,
    Hub MUST record the processed delivery's skipped/deferred reason rather than
    classify that refusal as an unexpected processing failure.
    Checks: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
    `test_webhook_records_why_a_trigger_did_not_enroll`,
    `test_webhook_notes_a_deferred_first_dispatch_after_enrolling`,
    `test_webhook_notes_an_advance_deferred_by_a_held_lease`.
11. **Unexpected processing failure**: IF event handling encounters an unexpected
    error, THEN Hub MUST retain a failed delivery outcome for diagnosis/recovery.
    Check: `modules/hub/tests/integration/features/project_management/github_webhooks/test_github_webhooks_api.py`,
    `test_failed_webhook_processing_is_acknowledged_for_polling_recovery`.
12. **Lost intake recovery**: WHEN a dispatcher tick finds a stalled received
    delivery eligible for replay, Hub MUST process its retained routing facts.
    Check: `modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py`,
    `test_a_lost_auto_run_delivery_is_replayed_by_the_next_tick`.

## 4. Interfaces & Data Contracts

| Surface | Request and result |
| --- | --- |
| `POST /api/github/webhooks` | GitHub headers and signed JSON object; HTTP 202 with `status: accepted` or `status: duplicate` |
| `POST /api/github/webhooks/deliveries/{delivery_id}/process` | Internal signed callback; normal handling returns HTTP 204; missing/invalid callback authority returns HTTP 401 |
| `GET /api/v1/github-webhook-deliveries` | Signed-in human read access; `offset >= 0`, `limit` 1–100 (default 50), optional `status`, `repository`, `noteworthy`; returns `items` and `total_count` |

Intake requires `X-GitHub-Delivery`, `X-GitHub-Event` and
`X-Hub-Signature-256: sha256=<HMAC>`. HMAC-SHA256 covers the exact body bytes.
Missing delivery/event headers or an invalid JSON-object body returns HTTP 400;
an unset `GITHUB_WEBHOOK_SECRET` returns HTTP 503. These additional validation
branches are source-inspected; the cited intake tests explicitly exercise signature
failure and duplicate/success responses.

Persisted fields are delivery/event identity, lowercased repository, payload digest,
PR number, `auto_run`, optional requested catalog, timestamps, attempts, processing
status and safe outcome detail. The raw body is not retained. `@auto-run` matching
is case-insensitive; an optional `:<catalog key or kind>` passes catalog selection
to enrollment. PR opened/reopened bodies and created comments on PRs supply trigger
text; ordinary Issue comments and deleted comments do not. Existing runs can be
advanced by matching PR/workflow events without another trigger mention.

A generated callback contains `X-Autohub-Task-Expires` and
`X-Autohub-Task-Signature`, signed in a separate message domain using the webhook
secret and delivery ID. Generated signatures last one hour. Task creation uses a
four-second HTTP timeout and requests a 60-second Cloud Tasks dispatch deadline.
Unset/failed queuing falls back to background work; an uncertain queue creation can
still produce a callback, so domain enrollment and advancement retain their own
idempotency/lease boundaries. The callback records normal processing failures on
the delivery; infrastructure failures can still fail the callback request.

### Scheduler replay boundary

The sweep selects at most 20 deliveries per pass. Candidates are older than two
minutes but younger than 24 hours, have fewer than two recorded handling attempts,
and are either `received` or `failed` with `auto_run=true`. A conditional
state/attempt update claims each candidate as `retrying` before handling. The
handler records `processed` or `failed` and increments the attempt count.

These exact ages, count limits and conditional-claim semantics derive from
`usecases.py` and `repos.py`; the cited tick regression exercises delayed received
replay, not every boundary or concurrent crash outcome. Already `retrying` rows
are not fresh sweep candidates. Polling advances an enrolled PR independently;
it does not reconstruct an enrollment trigger whose stored facts never existed.
The delivery rows' separate 90-day retention belongs to
`CAP-EXEC-scheduling-maintenance`.

## 5. Source and verification evidence

Source inspected: `modules/hub/app/features/project_management/github_webhooks/`,
`modules/hub/app/features/execution/dispatchers/usecases/housekeeping.py` and
`modules/hub/app/router.py`. Named tests were inspected, not executed for this
contract. They use local database and controlled HTTP/provider boundaries; they
do not establish deployed Cloud Tasks delivery or live GitHub event processing.

Use [deployment operations](../../operations/cloud-run-deployment.md#61-webhook-processing-queue-cloud-tasks-recommended)
for queue provisioning and [operator diagnosis](../../operations/operator-notices.md)
for delivery-history inspection.
