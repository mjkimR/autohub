---
id: UX-catalog-connector
title: Catalog connector
summary: "Assign the Connector used by an AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-connector] Catalog connector

## 1. Purpose

- **Primary task**: Assign the Connector used by an AI catalog.
- **Facts to commit**: The selected catalog and required provider; disabled connectors remain labelled.
- **Secondary items**: The catalog list remains behind this editor.

## 2. Content

The selected policy editor is primary; its explanatory text appears beside or below its fields.

- AI catalog (identity).
- Connector (provider-filtered selector): includes No connector and matching disabled entries.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save connector | `UC-configure-agent-catalog` 2a | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | The catalog refreshes with the saved connector assignment. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CatalogConnectorDialog.svelte`.
