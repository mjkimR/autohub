---
id: UX-catalog-daily-quota
title: Catalog quota policy
summary: "Set the daily-task quota policy of a Jules AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-daily-quota] Catalog quota policy

## 1. Purpose

- **Primary task**: Set the daily-task quota policy of a Jules AI catalog.
- **Facts to commit**: The account allowance, rolling versus calendar window, and calendar reset timezone.
- **Secondary items**: The catalog list remains behind this editor.

## 2. Content

The selected policy editor is primary; its explanatory text appears beside or below its fields.

- AI catalog (daily quota editor): positive integer Daily task limit.
- AI catalog (window selector): Rolling 24 hours or Calendar day.
- Reset timezone: shown for Calendar day; accepts an IANA timezone.
- Quota explanation: counted tasks and hold affect admission, not provider entitlement.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save quota policy | `UC-configure-agent-catalog` 2a | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | The policy is saved and the catalog list reloads. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/DailyQuotaPolicyDialog.svelte`.
