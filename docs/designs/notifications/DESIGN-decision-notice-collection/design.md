---
id: DESIGN-decision-notice-collection
title: "Decision notice collection and delivery passes"
status: active
area: notifications
summary: "Explains how a shared maintenance pass rotates Decision subscriptions, scans decision discovery, leases one message per channel and records its outcome, and why an eligible notice can wait several passes; guarantees stay with CAP-NOTIFY-operator-notifications."
related_capabilities: [CAP-NOTIFY-operator-notifications, CAP-PR-operator-decisions]
related_usecases: [UC-receive-decision-notice]
related_operations: [OPS-operator-notice-absence-routing]
entrypoints:
  - modules/hub/app/features/notifications/decision_worker.py
  - modules/hub/app/features/notifications/decision_repo.py
  - modules/hub/app/features/notifications/decision_service.py
---

# [DESIGN-decision-notice-collection] Decision notice collection and delivery passes

Decision notices are produced only inside shared maintenance, which runs on external ticks and also serves other
owners. Each pass therefore touches only a few channels, reads only part of the persisted decision discovery, and
sends at most one message per channel. Hub never repeats a send whose outcome it could not confirm. An operator
asking why a waiting decision has produced no notice needs to know which of those bounds held it back. The
eligibility, timing and uncertainty guarantees belong to `CAP-NOTIFY-operator-notifications` §6.

## One maintenance pass

The maintenance task in
[task.py](../../../../modules/hub/app/features/execution/tasks/domains/maintenance/task.py) calls
`DecisionNoticeWorker.tick` last, after history retention, Work Issue synchronization, activity settlement, SDK flow
maintenance and the connection-test and provider-catalog workers. An exception from the
notice pass is logged and does not fail maintenance. `tick` in
[decision_worker.py](../../../../modules/hub/app/features/notifications/decision_worker.py) runs under a 45-second
timeout.

1. `next_channels` in [decision_repo.py](../../../../modules/hub/app/features/notifications/decision_repo.py) locks
   the `decision-notices` row of `decision_notice_queue`. It selects up to four channels that have an enabled
   subscription or a `sending` attempt, in channel-ID order after the stored cursor, and wraps to the start when
   none remain. It then stores the last selected ID as the new cursor.
2. For each selected channel, in order, `collect` runs and, if it admitted an attempt, `deliver` sends it before
   the next channel. An exception in one channel is logged and the next channel continues. If the timeout ends the
   pass, the remaining channels wait for the next pass's rotation.

With more than four active channels, a channel is therefore visited only on every second or later pass.

## Collection for one channel

`collect` runs in one transaction:

1. Mark the channel's `sending` attempts whose 60-second lease has expired, and their notices, `unknown`
   (`lease-expired`).
2. Stop if the subscription is disabled, or the channel is disabled or its minimum level excludes `warning`.
3. Load up to 100 `pending` notices for the current destination generation.
4. Scan up to 100 discovery entries of nonterminal Runs, ordered by (`waiting_since`, `key`) and starting after the
   subscription's `scan_time`/`scan_key` cursor. Each entry that matches the subscription's kinds and projects and
   is not already known becomes a `pending` notice for (destination generation, key, fingerprint). A notice that
   already has an attempt is never made pending again.
5. Move the scan cursor to the last scanned entry. An empty scan clears the cursor, so the next visit rescans from
   the start.
6. Re-read each pending notice's discovery entry. A missing entry, a finished Run or a changed fingerprint marks it
   `superseded`. An entry that no longer matches the filters stays `pending` without being sent.
7. If nothing is sendable, clear `digest_since` and stop. Otherwise set `digest_since` if it is empty. A `digest`
   subscription stops here until 15 minutes after `digest_since`.
8. Build the message from at most ten sendable notices, stopping before the text would exceed 3,500 characters.
   Admit one attempt holding the frozen message, the notice IDs, the destination generation, a random token and a
   lease 60 seconds out. Mark the included notices `sending`.

Notices left out of the message stay `pending` for a later pass.

## Delivery and outcome fence

`deliver` reads the attempt and returns early if it is no longer `sending` or its lease has expired. A destination
generation that changed after admission records `failed` (`destination-rotated`). A missing or undecryptable token
records `failed` (`missing-destination`). Otherwise it sends once through
[decision_transport.py](../../../../modules/hub/app/features/notifications/decision_transport.py), outside any
database transaction, with a ten-second timeout.

| Telegram result | State | Detail |
| --- | --- | --- |
| HTTP 200 with `ok: true` | `accepted` | none |
| HTTP 4xx with `ok: false` | `failed` | `telegram-refused` |
| Request error, non-JSON body or any other response | `unknown` | `transport-unconfirmed` |

The outcome is written only if the attempt is still `sending` with the same token and an unexpired lease. A result
that arrives after expiry is discarded, and the attempt keeps the `unknown` state that step 1 of a later `collect`
gives it. Each written outcome also compacts history: terminal attempts beyond the newest 100 are deleted, at most
100 at a time.

## Persisted state read back by later passes

| Table | Fields read on later passes |
| --- | --- |
| `decision_notice_queue` | `cursor`: last channel ID visited |
| `decision_subscriptions` | `enabled`, `settings` (`mode`, `kinds`, `project_scope`, `project_ids`, `review_origin`), `scan_time`, `scan_key`, `digest_since` |
| `decision_notices` | Unique (`channel_id`, `destination_generation`, `decision_key`, `fingerprint`); `state` (`pending`, `sending`, `accepted`, `failed`, `unknown`, `superseded`), `last_attempt_id`, `observed` |
| `decision_notice_attempts` | `notice_ids`, `message`, `state`, `token`, `lease_expires_at`, `outcome_at`, `detail`, `destination_generation` |

## Why a waiting decision has no notice yet

In addition to the subscription gates in `CAP-NOTIFY-operator-notifications` rules 12 and 13, a matching decision
stays without an attempt while any of these holds:

- Its channel has not been visited since the decision appeared, because of the four-channel rotation or no
  maintenance tick.
- The subscription's scan cursor has not reached the entry yet.
- A `digest` subscription is inside its 15-minute wait.
- The previous message reached its ten-notice or 3,500-character cap.
- The channel's 100 oldest pending notices come before it.

## Authority boundary

- `CAP-NOTIFY-operator-notifications` §6 rules 12 to 24 own subscription gates, eligibility, admission
  serialization, message bounds, timing, uncertainty, deduplication, rotation and resend.
- `CAP-PR-operator-decisions` owns decision discovery entries, keys and fingerprints.
- `ARCH-06-execution` owns where this pass runs within shared maintenance and its lock order.
- `ADR-decision-notice-delivery` records why polling and retained uncertainty were chosen.

## Update triggers

- `DecisionNoticeWorker.tick`, `collect` or `deliver`, or `next_channels`, `scan`, `generations` or `compact`,
  change a bound (45 seconds, four channels, 100 entries or notices, ten links, 3,500 characters, 15 minutes,
  60-second lease) or the order of steps.
- `send_decision_message` changes its outcome classification.
- The maintenance task moves the notice pass relative to its other owners.
- Recheck with `just test modules/hub/tests/integration/features/notifications/test_decision_notices.py`.
