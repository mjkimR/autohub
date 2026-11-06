---
id: CAP-NOTIFY-operator-notifications
title: Operator notification channels
summary: "Auto Hub sends severity-filtered operator notices through encrypted Telegram channel settings and records delivery outcomes. Notices report work needing attention without authorizing or controlling that work."
area: notifications
status: active
usecases:
  - UC-receive-decision-notice
  - UC-configure-operator-notifications
entrypoints:
  - modules/hub/app/features/notifications/api/v1.py
  - modules/hub/app/features/notifications/usecases.py
  - modules/hub/app/features/notifications/decision_api.py
---

# [CAP-NOTIFY-operator-notifications] Operator notification channels

## 1. Summary

Operators configure Telegram destinations independently of provider connectors.
Explicit channel tests return delivery evidence; background notices report stopped
or waiting runs, trigger recovery and other operator-facing events without making
the underlying work depend on successful notification delivery.

## 2. Scope & Boundary

- **In-Scope**: channel configuration, sealed bot tokens, severity selection,
  explicit test delivery, recorded delivery status, decision subscriptions and tick-driven stop notices.
- **Out-of-Scope**: Telegram account/chat setup and transport availability; run
  authorization and execution remain with their owning domain capabilities.
- **Scope Excluded**: inbound commands, provider authentication through channels,
  additional channel kinds and a durable retry queue for generic emitted notices. Decision notices have their own retained evidence.

## 3. Business Rules & Policies

1. **Secret storage**: WHEN a channel is created or its token is rotated, Hub MUST
   seal the token using the channel identity and notification-specific encryption
   scope rather than store it in the public configuration.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
2. **Secret omission**: WHEN returning a channel, Hub MUST omit its bot token and
   encrypted credential fields from the response.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
3. **Unique names**: IF another channel already has the requested name, THEN Hub
   MUST reject channel creation or renaming with HTTP 409.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
   The cited API example covers duplicate creation. Rename rejection is implemented
   in `modules/hub/app/features/notifications/services.py`; no dedicated rename
   assertion is cited here.
4. **Broadcast selection**: WHEN broadcasting a notice, Hub MUST target only enabled
   channels whose minimum severity admits the notice level.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
5. **Explicit tests**: WHEN testing a named channel, Hub MUST attempt that channel
   irrespective of its enabled flag or severity threshold.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
6. **Test outcome**: WHEN a channel test completes, Hub MUST report Telegram delivery
   acceptance or failure through `delivered` and `detail` rather than treat a
   transport refusal as a successful delivery.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
7. **Delivery state**: WHEN a delivery outcome is persisted, Hub MUST update
   `last_error` and set `last_sent_at` only on successful delivery.
   Test: `modules/hub/tests/integration/features/notifications/test_notification_channels_api.py`.
8. **Background isolation**: IF there is no working channel, THEN Hub MUST continue
   a dispatcher tick without making notification failure fail that tick.
   Test: `modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py`.
9. **Stop acknowledgement**: WHEN announcing a stopped or waiting run revision,
   Hub MUST mark that revision announced only after at least one channel succeeds.
   Test: `modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py`.
10. **Trigger visibility**: WHEN reporting deep health, Hub MUST distinguish a
    trigger that never fired, a trigger silent for more than ten minutes and a
    trigger within that interval as `never`, `stale` and `ok` respectively.
    Test: `modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py`.

11. **Trigger recovery notice**: WHEN a tick follows more than ten minutes of
    recorded trigger silence, Hub MUST attempt an informational resumed-trigger
    notice.
    Test: `modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py`,
    `test_health_reports_the_trigger_and_a_resumed_trigger_is_announced`.

## 4. Interfaces & Data Contracts

All channel routes require a signed-in person through the ordinary REST boundary.

| Method and path | Contract |
| --- | --- |
| `GET /api/v1/notification-channels` | Returns `{items: [...]}` with token-free channel summaries |
| `POST /api/v1/notification-channels` | Creates a channel; HTTP 201; accepts `name`, `chat_id`, `bot_token`, optional `kind`, `enabled`, `min_level` |
| `PATCH /api/v1/notification-channels/{channel_id}` | Changes supplied non-null settings; omitting `bot_token` preserves the token; unknown ID returns HTTP 404 |
| `DELETE /api/v1/notification-channels/{channel_id}` | HTTP 204 on deletion; unknown ID returns HTTP 404 |
| `POST /api/v1/notification-channels/{channel_id}/test` | HTTP 200 with `{delivered: boolean, detail: string or null}`; unknown ID returns HTTP 404 |

The supported kind is `telegram`. Defaults are `enabled=true` and `min_level=info`;
levels ascend through `debug`, `info`, `warning`, `error`, `critical`. Channel read
models contain identity/timestamps, name, kind, enabled flag, minimum level,
`chat_id`, `last_sent_at` and `last_error`. Invalid schema values return HTTP 422.

The Telegram transport sends plain text with a level prefix, no web preview, a
4,096-character cap and a ten-second HTTP timeout. A successful send certifies
transport acceptance, not that a person read the notice. Broadcasting and state
persistence do not form a transaction with Telegram, so duplicate delivery after
an uncertain failure is possible.

Tick housekeeping considers recent unannounced run stops within a 24-hour horizon.
A new stopped revision can be announced again. An undelivered revision remains
eligible on a later tick; absence of all external traffic cannot generate a
stopped-trigger notice from a separate resident timer.

### Notice categories

| Event | Level | Selection |
| --- | --- | --- |
| Run stopped | `error` | Unannounced `paused`, `blocked` or `failed` run revision within the 24-hour horizon |
| Run waiting | `warning` | Unannounced in-flight revision with a retained wait reason |
| Trigger resumed | `info` | Tick after more than ten minutes of recorded silence |
| Trigger stopped | `warning` | Webhook traffic observes a tick older than ten minutes; attempt at most once per hour |
| Login lockout | `warning` | Configured failed-login lockout; masked caller identity under `CAP-ACCESS-authentication-authorization` |
| Lost `@auto-run` | `error` | A replayed trigger still fails, under `CAP-PR-webhook-advancement` |
| Channel test | `info` | Explicit operator request |

The stopped-trigger warning's once-per-hour checkpoint and the exact stop-age
boundary derive from `housekeeping.py` and the run repository. The cited
housekeeping tests cover stopped-run acknowledgement, absent/failed channels,
health status and resumed-trigger notices; they do not establish dedicated
boundary tests for every warning throttle or age cutoff.

## 5. Evidence and operational guidance

Sources inspected: `modules/hub/app/features/notifications/`,
`modules/hub/app/features/execution/dispatchers/usecases/housekeeping.py`,
`modules/hub/app/router.py` and `modules/hub/app/auth.py`. The referenced tests use
controlled Telegram responses and were inspected as enforcement evidence. This
document claims neither a newly executed test nor live Telegram delivery.

See [operator notices](../../operations/operator-notices.md) for Telegram setup
and diagnosis. Transport settings above are established
by source inspection; no separate live transport coverage is asserted.

## 6. Decision notices

`ADR-decision-notice-delivery` records the ownership and uncertainty decision.

12. **Opt-in gates**: WHERE a Decision subscription is enabled, Hub MUST require trusted-destination confirmation, nonempty kinds, selected existing projects or explicit all-project scope, valid review origin and matching destination generation. Check: `modules/hub/tests/integration/features/notifications/test_decision_notices.py`.
13. **Effective eligibility**: WHEN admitting a decision notice, Hub MUST compose subscription project/kind selection with enabled channel and warning-level severity admission. Check: `test_decision_notices.py`.
14. **Observed evidence**: WHEN collecting notices, Hub MUST read persisted actionable discovery for nonterminal Runs without provider evaluation or owner mutation. Check: `test_decision_notices.py` and review of `decision_worker.py`.
15. **Generation admission**: WHEN competing workers admit the same channel/destination-generation/key/fingerprint, Hub MUST serialize channel ownership into one durable attempt. Check: PostgreSQL `test_concurrent_admission_channel_lock_postgres` in `test_decision_notices.py`.
16. **Immutable bounded message**: WHEN admitting a message, Hub MUST freeze at most ten complete exact links within 3,500 characters and retain omitted matching work as pending. Check: `test_message_count_character_budget_and_pending_overflow` in `test_decision_notices.py`.
17. **Timing**: WHERE immediate mode is selected, Hub MUST admit only during an eligible maintenance pass. WHERE digest mode is selected, Hub MUST wait at least fifteen minutes after retained eligible work is observed. Neither mode promises a delivery deadline. Check: `test_digest_due_stale_suppression_and_lease` in `test_decision_notices.py`.
18. **Uncertain transport**: IF a send times out, lacks definite acceptance/refusal or loses its lease, THEN Hub MUST retain unknown delivery without automatic resend. Check: transport classification and late-lease tests in `test_decision_notices.py`.
19. **Retained deduplication**: WHEN detailed attempt history is compacted, Hub MUST preserve channel-lifetime generation evidence and immutable request results. Check: `test_send_dedupe_unknown_and_exact_resend` in `test_decision_notices.py`; bounded compaction source review.
20. **Destination rotation**: WHEN the actual chat or token changes, Hub MUST advance destination generation and disable the subscription until explicit reviewed enablement. Check: defaults/rotation/replay and revision-zero tests in `test_decision_notices.py`.
21. **Replay before eligibility**: WHEN an actor repeats the exact operation/request/payload, Hub MUST return its original receipt before checking current revision. Check: `test_defaults_rotation_replay_and_actor_outcome` in `test_decision_notices.py`.
22. **Explicit resend**: WHEN an operator confirms a failed or unknown notice resend, Hub MUST require the current subscription revision, destination generation, actionable subject and duplicate acknowledgement before retaining one request-bound attempt. Check: `test_send_dedupe_unknown_and_exact_resend` in `test_decision_notices.py`.
23. **Temporary suppression**: WHEN filters exclude a never-admitted generation, Hub MUST preserve its eligibility if the exact actionable generation matches restored filters. Check: parameterized filter restoration regression in `test_decision_notices.py`.
24. **Minimal disclosure**: WHEN rendering a decision notice, Hub MUST omit question/answer content and credentials. Check: message rendering tests and source review of `decision_service.py`.

Decision subscriptions default off, including migrated channels. Channel recipients are trusted for disclosed metadata; a chat participant is not thereby an authenticated Hub principal. All current and future projects is an explicit disclosure scope. Existing matching pending decisions can become eligible after enablement or filter expansion. Stopping/changing/deleting settings cannot recall a send already admitted.

### Decision interfaces

All routes use the existing authenticated human boundary under `/api/v1/notification-channels/{channel_id}`:

| Method and suffix | Contract |
| --- | --- |
| `GET /decision-subscription` | Current settings, revision, destination generation, chat, effective gates and observation time |
| `PUT /decision-subscription` | Immutable `request_id`, `expected_revision`, `expected_destination_generation` and reviewed settings |
| `GET /decision-notices` | Cursor-bounded generation history plus at most 100 retained attempts |
| `POST /decision-notices/{notice_id}/resend` | Exact request identity, reviewed revision/generation and `acknowledge_possible_duplicate` |
| `GET /decision-requests/{request_id}?operation={operation}` | Actor-bound original recorded result, separately from current subscription and attempt outcome; absent proof remains unknown |

Subscription revision zero still checks destination generation. Review origin is HTTPS or loopback HTTP without credentials, path, query or fragment. At most 100 distinct selected project IDs and six distinct kinds are accepted. The six kinds are the existing discovery kinds. Same UUID with changed payload or actor returns `DECISION_NOTICE_IDENTITY_CONFLICT`. Feature-owned 409/422 refusals return `DECISION_NOTICE_REFUSED`; pre-handler schema validation returns HTTP422 with field details. Ambiguous responses remain unknown; current settings cannot prove an original request result.

Transport state `accepted` means Telegram accepted the message, not that a person read it or applied a decision. Structured rejection is `failed`; timeout, malformed outcome and expired 60-second lease are `unknown`. A resend may duplicate a remotely accepted message. History compaction retains the newest 100 detailed attempts and removes at most 100 older terminal attempts per successful completion. Generation/request evidence remains until channel deletion.

Exact review links use the configured origin and `/decisions?decision_key=...&decision_fingerprint=...`. `CAP-PR-operator-decisions` owns exact indexed selection and owner review. `UC-access-hub` owns sign-in; `UC-receive-decision-notice` describes the navigation and explicit recovery goal. No notice grants approval, saves an answer or resumes execution.
