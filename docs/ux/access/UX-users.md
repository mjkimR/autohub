---
id: UX-users
title: Account approval screen
summary: "Let a superadministrator inspect account access, confirm an access change and review recent account-access history."
area: access
element: screen
status: active
usecases: []
capabilities:
  - CAP-ACCESS-authentication-authorization
---

# [UX-users] Account approval screen

## 1. Purpose

- **Primary task**: review and change account admission.
- **Facts to commit**: account identity, approval status, active status, administrator role and the selected access-change action.
- **Secondary items**: the inline confirmation and recent history appear below the account table; navigation stays in `UX-app-shell`. The existing browser-session use case does not model this administrative goal.

## 2. Content

The Account table is primary at `/admin/users`. A selected action adds a confirmation form below it, and History adds a separate section below the table.

- Account (table row): email, approval, Active/Suspended, Administrator/User and applicable actions; the current account is marked you.
- Account (confirmation): the selected action and email, an optional reason and a warning that existing sessions end.
- Account (history): latest 50 access events with action, time, actor and optional reason.
- Account (page controls): Refresh and 50-row Previous/Next controls.

## 3. States

- **loading**: Loading accounts is shown; await the result.
- **populated**: inspect accounts, choose an applicable action or read history.
- **empty**: No accounts found remains with refresh/navigation available.
- **forbidden**: Administrator access is required replaces the account controls.
- **error**: a load failure offers Refresh; mutation or history failures produce toasts.
- **confirming**: the inline action form offers Confirm change or Cancel.
- **saving**: relevant mutation/page controls are disabled while the change is submitted.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh or change page | global: account and machine administration is outside the browser-session goal | populated | loading |  | `CAP-ACCESS-authentication-authorization` | The table reloads or an error toast appears. |
| Choose Approve, Reject, Suspend, Activate or administrator change | global: account and machine administration is outside the browser-session goal | populated | confirming |  | `CAP-ACCESS-authentication-authorization` | The selected action and its session consequence appear in the confirmation form. |
| Confirm change | global: account and machine administration is outside the browser-session goal | confirming | saving |  | `CAP-ACCESS-authentication-authorization` | Success or refusal is toasted; selection/history clear and accounts reload. |
| Cancel change | global: account and machine administration is outside the browser-session goal | confirming | populated |  |  | The confirmation form closes without submitting. |
| History | global: account and machine administration is outside the browser-session goal | populated | populated |  | `CAP-ACCESS-authentication-authorization` | Recent changes or No changes recorded appear for the selected email. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | The selected management screen replaces this screen. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/auth/admin/UsersAdminView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/auth/admin/UsersAdminView.integration.test.ts`.
