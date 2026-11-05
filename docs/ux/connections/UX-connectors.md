---
id: UX-connectors
title: Connectors
summary: "Select or maintain the Connector used by a Project connection."
area: connections
element: screen
status: active
usecases:
  - UC-configure-project-connection
capabilities:
  - CAP-PROJ-project-connections
---

# [UX-connectors] Connectors

## 1. Purpose

- **Primary task**: Select or maintain the Connector used by a Project connection.
- **Facts to commit**: Provider identity, enabled state and whether a credential needs rotation; saved secrets are not displayed.
- **Secondary items**: Creation and editing use separate modals; project assignment stays in project configuration.

## 2. Content

The searchable connector table is primary beneath registration and refresh.

- Connector (table row): name, GitHub/Jules provider, active/disabled badge, creation time and Edit/Delete actions.
- Local search: matches name or provider within the loaded list.
- Connector editors: `UX-connector-create`, `UX-connector-edit`.
- Delete confirmation: browser confirmation warns that dependent projects may fail.

## 3. States

- **populated**: The table presents loaded connector rows; search, edit or register another.
- **empty**: No rows or no local matches; clear the search or register a connector.
- **loading**: Loading feedback replaces table data; wait for the request.
- **error**: A load error provides retry; mutation refusals produce toasts.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Register connector | `UC-configure-project-connection` 1 | populated | populated | `UX-connector-create` | `CAP-PROJ-project-connections` | The registration form opens. |
| Edit Connector | `UC-configure-project-connection` 1 | populated | populated | `UX-connector-edit` | `CAP-PROJ-project-connections` | The metadata/rotation form opens without the stored secret. |
| Refresh | global: refresh saved connector inventory | populated | loading |  | `CAP-PROJ-project-connections` | The list reloads or shows a retryable error. |
| Delete and confirm | global: maintain credential inventory outside the project-configuration goal | populated | populated |  | `CAP-PROJ-project-connections` | A dependency warning precedes deletion; a toast reports success or failure. |
| Navigate to Projects | global: shared application navigation | populated | populated | `UX-projects` |  | The Projects screen opens. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/connectors/ConnectorsView.svelte`.
