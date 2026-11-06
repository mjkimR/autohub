---
id: UX-decision-notice-history
title: Decision notice delivery history
summary: "Review channel-owned decision settings and transport evidence with explicit request recovery."
area: settings
element: modal
status: active
usecases:
  - UC-receive-decision-notice
capabilities:
  - CAP-NOTIFY-operator-notifications
---

# [UX-decision-notice-history] Decision notice delivery history

## 1. Purpose

Inspect whether a particular notice was accepted, refused or remains unknown, and explicitly review any resend. Owner decision progress is a separate exact link.

## 2. Content

A bounded newest-first generation list is primary, with current subscription/channel context above, retained attempts below and cursor navigation.

- Notification channel: name/chat and destination generation; last-loaded timestamp.
- Operator notice: kind/project/run references, generation and observation time; admitted/delivered/failed/unknown times and safe failure code; no question/answer body.
- State detail: Accepted by Telegram is not read/applied; Unknown may already have been delivered; superseded/owner-unavailable records are inspect-only.
- Open exact review link when a retained subject remains available; Open inbox for unavailable/superseded evidence.
- Send again review: current destination/filter context, explicit May duplicate acknowledgement for unknown, and Confirm send again/Cancel. Both definite failures and unknowns retain original history and create at most one attempt per request UUID.
- History compaction: older detailed attempts are compacted; retained generation state still prevents duplicate admission.

## 3. States

- **loading**: wait with Close available; resend disabled.
- **populated**: inspect/read; refresh or page; review an eligible failed/unknown notice.
- **empty**: No decision notice history; Close or open settings.
- **error**: keep prior observations and time, offer Refresh; mutation controls unavailable until current basis loads.
- **reviewing-resend**: show current basis and duplicate warning where needed; Cancel or Confirm.
- **sending**: lock resend controls; preserve the request intent.
- **unknown-resend**: show request ID, Check outcome and Retry same resend command; no changed-payload request. Closing/reopening retains active session intent; full reload recovers only durable history and explicitly labels unavailable unacknowledged intent.
- **changed**: subscription or generation changed; no send, Refresh for review or Open inbox.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open exact review | `UC-receive-decision-notice` 1 | populated | loading | `UX-decision-inbox` | `CAP-NOTIFY-operator-notifications` | Exact link authenticates and inspects its owner; no authority is embedded. |
| Review send again | `UC-receive-decision-notice` 4 | populated | reviewing-resend | | `CAP-NOTIFY-operator-notifications` | Current destination/generation and possible duplicate are disclosed. |
| Confirm send again | `UC-receive-decision-notice` 4, `UC-receive-decision-notice` 4a | reviewing-resend | sending | | `CAP-NOTIFY-operator-notifications` | One durable resend attempt is admitted; receipt shown independently of owner progress. |
| Refresh / page | global: browse bounded transport evidence | populated, error | loading | | | Current page and time reload; no send occurs. |
| Refresh for review | `UC-receive-decision-notice` 4c | changed | populated | | `CAP-NOTIFY-operator-notifications` | Reloads current subscription/destination/generation in this modal and clears duplicate acknowledgement. |
| Open inbox | `UC-receive-decision-notice` 4b | changed | populated | `UX-decision-inbox` | | Opens current discovery without selecting a replacement. |
| Check outcome / Retry same resend | `UC-receive-decision-notice` 4a | unknown-resend | unknown-resend, populated | | `CAP-NOTIFY-operator-notifications` | Reads retained command evidence or replays its identical UUID/payload. |
| Cancel review | global: return to this history list without another attempt | reviewing-resend | populated | | | Discards only resend confirmation; retained uncertain request stays intact. |
| Close | global: leave history without another attempt | populated, unknown-resend, empty, error | populated | close | | Parent remains; uncertain session intent is not silently replaced. |
