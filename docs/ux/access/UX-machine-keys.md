---
id: UX-machine-keys
title: Machine keys panel
summary: "Show one machine's key metadata, issue a key and confirm revocation while keeping the one-time secret in a separate notice."
area: access
element: panel
status: active
usecases: []
capabilities:
  - CAP-ACCESS-authentication-authorization
---

# [UX-machine-keys] Machine keys panel

## 1. Purpose

- **Primary task**: issue or revoke a Machine key for the expanded machine.
- **Facts to commit**: the machine identity/activation, key label, optional expiration and the key selected for revocation.
- **Secondary items**: a successful issue reveals `UX-issued-machine-key` above the metadata table; `UX-machines` owns expansion and activation.

## 2. Content

This panel occupies the expanded machine table row. Key metadata is primary; issuance follows the list.

- Machine key (metadata row): label, created time, optional expiry and Active/Expired/Revoked status.
- Machine key (issuance form): required label and optional local date/time expiry; inactive machines disable issuance.
- Machine key (revocation confirmation): Confirm revoke and Cancel replace Revoke on the selected row.
- Machine key (one-time secret): `UX-issued-machine-key` appears only after successful issuance.

## 3. States

- **loading**: Loading keys is shown while metadata loads; the issuance form remains separate.
- **populated**: inspect key status, issue a labeled key or select a non-revoked key.
- **empty**: No keys issued leaves the issuance form available for an active machine.
- **confirming**: a selected row requires Confirm revoke or Cancel.
- **saving**: mutation controls are disabled until completion.
- **inactive**: Activate the machine before issuing keys explains why Issue key is disabled.
- **error**: a toast reports load/issue/revoke failures; the displayed panel remains available.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Issue key | global: account and machine administration is outside the browser-session goal | populated | saving | `UX-issued-machine-key` | `CAP-ACCESS-authentication-authorization` | The one-time secret appears after success and metadata reloads. |
| Revoke | global: account and machine administration is outside the browser-session goal | populated | confirming |  | `CAP-ACCESS-authentication-authorization` | The row exposes explicit confirmation and cancellation. |
| Confirm revoke | global: account and machine administration is outside the browser-session goal | confirming | saving |  | `CAP-ACCESS-authentication-authorization` | A result toast appears, confirmation clears and metadata reloads. |
| Cancel revoke | global: account and machine administration is outside the browser-session goal | confirming | populated |  |  | The row returns to its normal actions. |
| Hide keys on the parent row | global: collapse the selected machine details | populated | populated | `UX-machines` |  | The parent removes this panel. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/auth/machines/MachineKeysPanel.svelte`. Inspected check: `modules/hub-ui/src/lib/features/auth/machines/MachinesAdminView.integration.test.ts`.
