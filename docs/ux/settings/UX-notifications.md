---
id: UX-notifications
title: Notification channels
summary: "Test and maintain Notification channels used for Operator notices."
area: settings
element: screen
status: active
usecases:
  - UC-configure-operator-notifications
capabilities:
  - CAP-NOTIFY-operator-notifications
---

# [UX-notifications] Notification channels

## 1. Purpose

- **Primary task**: Test and maintain Notification channels used for Operator notices.
- **Facts to commit**: Destination chat, minimum level, enabled state and the last accepted or failed delivery.
- **Secondary items**: The channel form is `UX-notification-editor`; obtaining Telegram credentials remains external setup.

## 2. Content

Channel cards are primary below the add and refresh controls.

- Notification channel (card): name, kind/chat, minimum level and enabled badge.
- Delivery summary: last-delivered time or Nothing delivered yet; stored failure detail when present.
- Notification channel editor: `UX-notification-editor`.
- Empty guidance: BotFather, initial bot conversation, chat ID lookup, and an explicit test.

## 3. States

- **populated**: Cards offer Send test, Edit, Enable/Disable and Delete.
- **empty**: Setup guidance and Add Telegram channel offer a next action.
- **loading**: Initial loading text replaces cards; Refresh is disabled while loading.
- **testing**: Send test is disabled for the channel being tested; other channel cards remain available.
- **error**: Load failure offers retry; delivery/mutation failures appear in toasts, with persisted delivery failure shown after reload.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Add Telegram channel | `UC-configure-operator-notifications` 1 | populated | populated | `UX-notification-editor` | `CAP-NOTIFY-operator-notifications` | A blank channel form opens. |
| Edit | `UC-configure-operator-notifications` 4a | populated | populated | `UX-notification-editor` | `CAP-NOTIFY-operator-notifications` | The destination and severity are editable; the saved token is absent. |
| Send test | `UC-configure-operator-notifications` 3, `UC-configure-operator-notifications` 4 | populated | testing |  | `CAP-NOTIFY-operator-notifications` | A success/failure toast appears and the delivery summary reloads. |
| Enable or Disable | global: control future broadcast eligibility | populated | populated |  | `CAP-NOTIFY-operator-notifications` | The badge reloads with the saved value. |
| Delete and confirm | global: remove a destination after confirmation | populated | populated |  | `CAP-NOTIFY-operator-notifications` | The browser asks for confirmation, then a toast and reload report the outcome. |
| Refresh | global: reload channel configuration and delivery observations | populated | loading |  | `CAP-NOTIFY-operator-notifications` | Cards reload or a retryable load error appears. |
| Navigate to Projects | global: shared application navigation | populated | populated | `UX-projects` |  | The Projects screen opens. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/notifications/NotificationsView.svelte`.
