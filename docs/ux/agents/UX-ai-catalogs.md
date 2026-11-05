---
id: UX-ai-catalogs
title: AI catalogs
summary: "Inspect AI catalogs and choose the admission control or session history to manage."
area: agents
element: screen
status: active
usecases:
  - UC-configure-agent-catalog
  - UC-run-agent-session
capabilities:
  - CAP-AGENT-catalog-admission
  - CAP-AGENT-provider-sessions
---

# [UX-ai-catalogs] AI catalogs

## 1. Purpose

- **Primary task**: Inspect AI catalogs and choose the admission control or session history to manage.
- **Facts to commit**: Provider, availability source/time, configured versus effective capacity and current work counts.
- **Secondary items**: Each editor is a separate modal; broader navigation uses the shared application shell.

## 2. Content

Catalog cards are the primary region below the add and refresh controls.

- AI catalog (card): name/key/provider, availability badge and time, source/note, queued/active work counts and configured/effective concurrency.
- AI catalog (provider policy summary): Codex refresh cycles or Jules daily quota.
- Connector (assignment summary): shown for a connector-backed catalog.
- Editors: `UX-catalog-create`, `UX-catalog-availability`, `UX-catalog-concurrency`, `UX-catalog-connector`, `UX-catalog-daily-quota`, `UX-catalog-codex-refresh`.
- Provider session (history modal): `UX-catalog-sessions`, available for a connector-backed catalog.

## 3. States

- **populated**: Cards expose the controls supported by their catalog kind; disabled catalogs show a dispatch-disabled message.
- **empty**: The card region is empty; Add catalog remains the next action.
- **loading**: Initial load shows loading text; refresh and creation are disabled while loading.
- **error**: LoadError replaces the card region and offers retry; the page header remains.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh | `UC-configure-agent-catalog` 1 | populated | loading |  | `CAP-AGENT-catalog-admission` | Loading feedback is followed by current cards or a retryable load error. |
| Add catalog | `UC-configure-agent-catalog` 2 | populated | populated | `UX-catalog-create` | `CAP-AGENT-catalog-admission` | The creation form opens. |
| Connector | `UC-configure-agent-catalog` 2a | populated | populated | `UX-catalog-connector` | `CAP-AGENT-catalog-admission` | The selected catalog editor opens. |
| Concurrency | `UC-configure-agent-catalog` 2a | populated | populated | `UX-catalog-concurrency` | `CAP-AGENT-catalog-admission` | The selected catalog editor opens. |
| Set refresh time | `UC-configure-agent-catalog` 2a | populated | populated | `UX-catalog-availability` | `CAP-AGENT-catalog-admission` | The selected catalog editor opens. |
| Quota policy (Jules) | `UC-configure-agent-catalog` 2a | populated | populated | `UX-catalog-daily-quota` | `CAP-AGENT-catalog-admission` | The selected catalog editor opens. |
| Refresh policy (Codex) | `UC-configure-agent-catalog` 2a | populated | populated | `UX-catalog-codex-refresh` | `CAP-AGENT-catalog-admission` | The selected catalog editor opens. |
| Clear hold | `UC-configure-agent-catalog` 2a | populated | populated |  | `CAP-AGENT-catalog-admission` | A success toast and reload show the resulting availability. |
| Enable or Disable | `UC-configure-agent-catalog` 5a | populated | populated |  | `CAP-AGENT-catalog-admission` | The enabled badge and dispatch restriction update; existing hold details remain. |
| Sessions (Jules) | `UC-run-agent-session` 7 | populated | populated | `UX-catalog-sessions` | `CAP-AGENT-provider-sessions` | Session history opens for the chosen catalog. |
| Navigate to Projects | global: shared application navigation | populated | populated | `UX-projects` |  | The Projects screen opens. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/ai-catalogs/AICatalogsView.svelte`.
