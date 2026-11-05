---
id: UX-catalog-concurrency
title: Catalog concurrency
summary: "Set the shared concurrent-work limit for an AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-concurrency] Catalog concurrency

## 1. Purpose

- **Primary task**: Set the shared concurrent-work limit for an AI catalog.
- **Facts to commit**: Catalog identity and the distinction between configured and effective concurrency.
- **Secondary items**: The catalog list remains behind this editor.

## 2. Content

The selected policy editor is primary; its explanatory text appears beside or below its fields.

- AI catalog (identity).
- AI catalog (concurrency editor): integer Concurrent work limit from 1 to 1000.
- Explanatory text: running work can finish after a lower limit is saved.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save limit | `UC-configure-agent-catalog` 2a | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | The configured limit is saved and the catalog list reloads. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CatalogConcurrencyDialog.svelte`.
