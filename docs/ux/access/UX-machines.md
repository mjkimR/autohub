---
id: UX-machines
title: Machine registration screen
summary: "Let a superadministrator register scoped machine identities, change activation and expand each machine's key controls."
area: access
element: screen
status: active
usecases: []
capabilities:
  - CAP-ACCESS-authentication-authorization
---

# [UX-machines] Machine registration screen

## 1. Purpose

- **Primary task**: manage the machine identities that own Machine keys.
- **Facts to commit**: a machine name, selected installation-wide scopes and the effect of deactivation on all its keys.
- **Secondary items**: the selected machine expands `UX-machine-keys`; human account controls remain in `UX-users`.

## 2. Content

The New machine form precedes the primary machine table at `/admin/machines`. Scope hints describe each permission before creation.

- Machine (registration form): constrained name and selected scope checkboxes.
- Machine (table row): name, scopes, Active/Inactive and Keys/Hide keys plus Activate/Deactivate controls.
- Machine key (expanded controls): `UX-machine-keys` appears only for the selected machine.
- Administrative access (notice): denies the surface to a non-superadministrator.

## 3. States

- **loading**: initial profile/list loading shows a progress message; wait or navigate elsewhere.
- **populated**: create a named machine with at least one scope, expand keys or change activation.
- **empty**: No machines yet leaves registration available.
- **forbidden**: Administrator access is required leaves no machine controls.
- **error**: loading or mutations show a toast; Refresh is available for an authorized profile.
- **saving**: shared busy state disables registration and activation until a response arrives.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Create machine | global: account and machine administration is outside the browser-session goal | populated | saving | `UX-machine-keys` | `CAP-ACCESS-authentication-authorization` | Success clears the form, reloads machines and expands the created identity; duplicate or failed creation is toasted. |
| Keys or Hide keys | global: account and machine administration is outside the browser-session goal | populated | populated | `UX-machine-keys` | `CAP-ACCESS-authentication-authorization` | The chosen key panel expands or collapses. |
| Activate or Deactivate | global: account and machine administration is outside the browser-session goal | populated | saving |  | `CAP-ACCESS-authentication-authorization` | A result toast appears and the list reloads; deactivation rejects the machine keys on later requests. |
| Refresh | global: account and machine administration is outside the browser-session goal | populated | loading |  | `CAP-ACCESS-authentication-authorization` | Machine state is reloaded. |
| Navigate through the console | global: navigation between management surfaces | populated | populated | `UX-dashboard` |  | The selected management screen replaces this screen. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/auth/machines/MachinesAdminView.svelte`. Inspected check: `modules/hub-ui/src/lib/features/auth/machines/MachinesAdminView.integration.test.ts`.
