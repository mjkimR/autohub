---
id: UX-connector-create
title: Register connector
summary: "Register a Connector with encrypted provider credentials."
area: connections
element: modal
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-connector-create] Register connector

## 1. Purpose

- **Primary task**: Register a Connector with encrypted provider credentials.
- **Facts to commit**: The intended provider and connector identity; credential input affects later authenticated work.
- **Secondary items**: Cancel leaves the connector table unchanged.

## 2. Content

The credential/metadata form is the primary region.

- Connector (credential form): name, provider selector and required secret token.
- Secret visibility toggle: starts masked; GitHub and Jules provider choices have provider-specific placeholder text.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Register Connector | `UC-configure-project-connection` 1 | populated | saving | `UX-connectors` | `CAP-PROJ-project-connections` | Success closes the modal and refreshes the table; failure leaves it open with a toast. |
| Toggle password visibility | global: inspect only the locally entered secret | populated | populated |  |  | The current input switches between masked and visible text. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/connectors/ConnectorsView.svelte`.
