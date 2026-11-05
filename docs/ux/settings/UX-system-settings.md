---
id: UX-system-settings
title: System configurations
summary: "Inspect saved system configuration records."
area: settings
element: screen
status: active
usecases: []
capabilities: []
---

# [UX-system-settings] System configurations

## 1. Purpose

- **Primary task**: Inspect saved system configuration records.
- **Facts to commit**: The displayed name, JSON data and last-updated metadata; this screen exposes no write controls.
- **Secondary items**: Navigation remains in the shared application shell.

## 2. Content

Read-only configuration cards are primary below Refresh.

- System configuration (card): name and formatted JSON data.
- Record metadata: updated date and shortened ID.

## 3. States

- **populated**: Read the available JSON cards or refresh.
- **empty**: No system configurations defined is shown; refresh or navigate away.
- **loading**: Loading system configs text replaces the cards and Refresh is disabled.
- **error**: LoadError offers retry and List unavailable replaces the cards.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh | global: inspect current system configuration records | populated | loading |  |  | Cards reload or a retryable load error appears. |
| Navigate to Projects | global: shared application navigation | populated | populated | `UX-projects` |  | The Projects screen opens. |

## 5. Evidence

Implementation inspection: `modules/hub-ui/src/lib/features/configuration/system-configs/SystemConfigsView.svelte`.
