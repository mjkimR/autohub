---
id: UX-catalog-create
title: Add AI catalog
summary: "Create an AI catalog with its provider and initial work limits."
area: agents
element: modal
status: active
usecases:
  - UC-configure-agent-catalog
capabilities:
  - CAP-AGENT-catalog-admission
---

# [UX-catalog-create] Add AI catalog

## 1. Purpose

- **Primary task**: Create an AI catalog with its provider and initial work limits.
- **Facts to commit**: A unique permanent key, provider, account limits and an optional enabled Jules connector.
- **Secondary items**: Existing catalog policy controls remain on `UX-ai-catalogs`.

## 2. Content

The creation form is primary. Provider-specific fields appear below the common identity fields.

- AI catalog (creation form): Name, Catalog key, Provider, Concurrent work limit.
- Connector (Jules selector): enabled Jules entries and Connect later; shown only for Jules.
- AI catalog (initial quota): Daily task limit; shown only for Jules.
- Codex explanation: project GitHub/Codex setup supplies authentication; creating a catalog does not switch the signed-in account.

## 3. States

- **populated**: The current definition is editable; save or cancel.
- **saving**: The save control is disabled while the request runs.
- **error**: A refusal or request failure produces a toast and preserves the open form for correction or retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Create catalog | `UC-configure-agent-catalog` 2, `UC-configure-agent-catalog` 3, `UC-configure-agent-catalog` 4 | populated | saving | `UX-ai-catalogs` | `CAP-AGENT-catalog-admission` | Success closes the modal and inserts the saved catalog; a refusal shows a toast. |
| Cancel or dismiss | global: dismiss the editor without saving | populated | populated | close |  | The parent screen remains visible. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/CreateCatalogDialog.svelte`.
