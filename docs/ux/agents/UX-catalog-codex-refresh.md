---
id: UX-catalog-codex-refresh
title: Catalog refresh policy
summary: "Set the refresh cycles of a Codex AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-codex-refresh] Catalog refresh policy

## 1. Purpose

- **Primary task**: Set the refresh cycles of a Codex AI catalog.
- **Facts to commit**: Short-cycle enablement and the intended short and long refresh intervals.
- **Secondary items**: The catalog list remains behind this editor.

## 2. Content

The selected policy editor is primary; its explanatory text appears beside or below its fields.

- AI catalog (refresh-policy editor): Use short refresh cycle checkbox.
- Short cycle in hours: disabled when the checkbox is off.
- Long cycle in days.
- Quota explanation: cycles are measured from the usage window and include safety jitter.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save policy | `UC-configure-agent-catalog` 2a | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | The converted cycle settings are saved and the catalog list reloads. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CodexRefreshPolicyDialog.svelte`.
