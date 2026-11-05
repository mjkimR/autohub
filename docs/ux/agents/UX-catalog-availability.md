---
id: UX-catalog-availability
title: Set catalog refresh time
summary: "Set a global hold until a chosen local time for an AI catalog."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-availability] Set catalog refresh time

## 1. Purpose

- **Primary task**: Set a global hold until a chosen local time for an AI catalog.
- **Facts to commit**: The current availability, catalog identity and browser timezone.
- **Secondary items**: The catalog list remains behind this editor.

## 2. Content

The selected policy editor is primary; its explanatory text appears beside or below its fields.

- AI catalog (identity and current hold).
- AI catalog (availability editor): required local date/time and optional operator note.
- Local-time preview: Will resume with the browser timezone, or an instruction to enter a future time.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Save global hold | `UC-configure-agent-catalog` 2a | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | The chosen local time becomes a global catalog hold and the list reloads. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CatalogAvailabilityDialog.svelte`.
