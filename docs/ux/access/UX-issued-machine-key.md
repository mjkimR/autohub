---
id: UX-issued-machine-key
title: Issued machine key notice
summary: "Expose a newly issued key once, with scope-dependent MCP connection snippets and explicit acknowledgement that it was stored."
area: access
element: panel
status: active
usecases: []
capabilities:
  - CAP-ACCESS-authentication-authorization
  - CAP-MCP-tool-access
---

# [UX-issued-machine-key] Issued machine key notice

## 1. Purpose

- **Primary task**: store the newly issued Machine key before dismissing its one-time value.
- **Facts to commit**: key label/value and the warning that it cannot be retrieved later.
- **Secondary items**: compatible Work MCP endpoint and Operations MCP endpoint snippets follow the key, according to the machine scopes.

## 2. Content

The secret and warning are primary above connection instructions. The notice is part of `UX-machine-keys`, not a modal.

- Machine key (one-time value): full secret with Copy key and label.
- Work MCP endpoint (connection examples): shown for work read/write scopes.
- Operations MCP endpoint (connection examples): shown for operations scope.
- Machine key (configuration snippets): project/global tabs show Antigravity, Claude Code and Codex examples; Codex uses an environment-variable reference.
- Machine key (acknowledgement): I stored the key dismisses this value from the current panel.

## 3. States

- **populated**: the newly issued value is visible; copy/store it and then acknowledge.
- **project**: project-level connection examples are shown.
- **global**: user/global connection examples are shown.
- **copy-error**: a toast asks the operator to select/copy text manually.
- **dismissed**: the parent removes this notice; the secret cannot be recovered through key metadata.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Copy key or a connection example | global: account and machine administration is outside the browser-session goal | populated | populated |  |  | A copied toast confirms success; failure suggests manual copying. |
| Select Global | global: account and machine administration is outside the browser-session goal | project | global |  |  | Global configuration examples are displayed. |
| Select Project level | global: account and machine administration is outside the browser-session goal | global | project |  |  | Project configuration examples are displayed. |
| I stored the key | global: account and machine administration is outside the browser-session goal | populated | dismissed | `UX-machine-keys` | `CAP-ACCESS-authentication-authorization` | The one-time value disappears from the panel. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/lib/features/auth/machines/IssuedKeyNotice.svelte`. Inspected check: `modules/hub-ui/src/lib/features/auth/machines/MachinesAdminView.integration.test.ts`.
