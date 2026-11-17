---
id: OPS-operator-notice-absence-routing
title: "Missing operator notice diagnosis and routing"
status: active
summary: "Routes an expected Telegram operator notice that did not arrive to its owner through channel delivery state and filters, the scheduler trigger heartbeat and decision subscription and history evidence; Telegram transport and reading stay outside Hub evidence."
related_capabilities:
  - CAP-NOTIFY-operator-notifications
  - CAP-EXEC-scheduling-maintenance
related_usecases:
  - UC-configure-operator-notifications
  - UC-receive-decision-notice
related_designs:
  - DESIGN-decision-notice-collection
---

# [OPS-operator-notice-absence-routing] Missing operator notice diagnosis and routing

A run stopped, a decision is waiting or the trigger went silent, and no Telegram notice arrived. Notice delivery
never fails the work it reports, so the missing message leaves no error on the run, and a successful channel test
proves only that the destination accepts messages. Run-stop and trigger notices are produced only by dispatcher
ticks or webhook traffic, and decision notices only by shared maintenance; a silent channel therefore cannot tell
a broken destination, a filtered notice, a stopped trigger and a disabled subscription apart
(`CAP-NOTIFY-operator-notifications` §2, §4).

## Routing

`GET /api/v1/notification-channels` (Settings → Notifications, `UX-notifications`) returns each channel's
`enabled`, `min_level`, `last_sent_at` and `last_error`. `GET /api/health/deep` (System › Health, `UX-dashboard`)
reports `scheduler` `ok`, `stale` or `never` with `last_tick_at`; the screen labels them Firing, Stopped and Never
fired. Decision notices add `GET .../decision-subscription` for the effective gates and `GET .../decision-notices`
for retained attempts (`CAP-NOTIFY-operator-notifications` §6, Decision interfaces).

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| Destination refuses delivery | `last_error` is set and `last_sent_at` does not advance; **Send test** returns `delivered=false` with `detail` | [Configure Telegram](../runbooks/operator-notices.md#configure-telegram); `UC-configure-operator-notifications` extension 4a. |
| Notice filtered by channel settings | `last_error` is empty and **Send test** returns `delivered=true`, but the channel has `enabled=false` or a `min_level` above the notice level in the notice category table | `CAP-NOTIFY-operator-notifications` §3 rule 4 and §4, Notice categories; edit the channel in `UX-notification-editor`. |
| No tick-driven notice because the trigger is silent | `scheduler` is `stale` or `never`; run-stop and trigger-resumed notices wait for the next tick, and the stopped-trigger warning needs an accepted webhook delivery and repeats at most hourly | [Check whether the trigger is firing](../runbooks/operator-notices.md#check-whether-the-trigger-is-firing); `CAP-NOTIFY-operator-notifications` §3 rules 10 and 11. |
| Run stop not announced | `scheduler` is `ok` and the channel admits `error`, but the run's stopped revision is older than 24 hours, or it was already announced and has not changed revision since | `CAP-NOTIFY-operator-notifications` §4 (24-hour horizon, per-revision announcement); open the run itself through `UX-run-page`. |
| Decision notice never admitted | `decision-subscription` shows the subscription disabled, a blocking gate, a project or kind outside its selection, or a changed destination generation after a chat or token change | `UX-decision-subscription`; `CAP-NOTIFY-operator-notifications` §6 rules 12, 13 and 20; `UC-configure-operator-notifications` extension 6c. |
| Decision notice admitted but not delivered | `decision-notices` lists the generation with transport state `failed` or `unknown` | `UX-decision-notice-history` for a reviewed resend; `UC-receive-decision-notice` extension 4a; `CAP-NOTIFY-operator-notifications` §6 rules 18 and 22. |
| Decision notice still pending | `decision-notices` has no attempt for the decision; the subscription uses the 15-minute digest, the batch reached its ten-link or 3,500-character cap, the four-channel rotation or the subscription's discovery scan has not reached it yet, or no maintenance pass ran since the decision appeared | `CAP-NOTIFY-operator-notifications` §6 rules 16 and 17; `DESIGN-decision-notice-collection` for the per-pass bounds; the trigger row above when maintenance is not running. |
| Notice accepted but not seen | `last_sent_at` advanced at the expected time, or the decision attempt shows `accepted` | Telegram and the destination chat; acceptance is not reading (`CAP-NOTIFY-operator-notifications` §4). |

Check the channel row first, because a set `last_error` explains every category at once; check `scheduler` before
reading any run-stop or trigger notice as missing. For evidence that matches no row, correlate the expected notice
time with the application log as in [Logs and expired history](../runbooks/operator-notices.md#logs-and-expired-history),
since a failed broadcast is logged and not retried for generic notices.

## Normal-state observation

After the owner's action, **Send test** returns `delivered=true`, `last_error` is empty and `last_sent_at` advances
with the next admitted notice. System › Health shows the trigger as Firing with a recent `last_tick_at`. For
decision notices, the subscription shows no blocking gate and the next attempt reaches `accepted`.
`CAP-NOTIFY-operator-notifications` owns these facts.

## Authority boundary

No notice, test or resend grants approval, saves an answer or resumes work; `CAP-PR-operator-decisions` owns
decision review. The evidence cannot establish that a person read an accepted message, and an uncertain send can
still have reached the chat, so a resend can duplicate it (`CAP-NOTIFY-operator-notifications` §4, §6).
`CAP-EXEC-scheduling-maintenance` owns the trigger and maintenance schedule whose silence suppresses notices.

## Update triggers

- `CAP-NOTIFY-operator-notifications` §3 rules 4, 7, 9 to 11, the §4 notice category table or §6 rules 12 to 22
  change.
- The channel fields `enabled`, `min_level`, `last_sent_at` or `last_error`, or the deep-health `scheduler` values,
  change.
- The tick and webhook call sites of
  [housekeeping.py](../../modules/hub/app/features/execution/dispatchers/usecases/housekeeping.py) change.
- A channel kind other than `telegram` or a durable retry queue for generic notices is added.
