---
id: UX-notification-editor
title: Telegram channel editor
summary: "Save a Notification channel destination and minimum Operator notice severity."
area: settings
element: modal
status: active
usecases:
  - UC-configure-operator-notifications
capabilities:
  - CAP-NOTIFY-operator-notifications
---

# [UX-notification-editor] Telegram channel editor

## 1. Purpose

- **Primary task**: Save a Notification channel destination and minimum Operator notice severity.
- **Facts to commit**: A unique name, Telegram chat ID, minimum level and a bot token for creation or rotation.
- **Secondary items**: Delivery testing happens on `UX-notifications` after saving.

## 2. Content

The channel form is primary above Cancel and Save.

- Notification channel (destination form): Name, required Chat ID and Minimum notification level.
- Notification channel (secret input): masked Bot token, required for creation; blank on edit retains the stored token.
- The title identifies Add versus Edit mode; the saved token is never displayed.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save | `UC-configure-operator-notifications` 1, `UC-configure-operator-notifications` 2 | populated | saving | `UX-notifications` | `CAP-NOTIFY-operator-notifications` | Success closes the editor and reloads token-free cards; refusal leaves the editor open with a toast. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/notifications/NotificationsView.svelte`.
