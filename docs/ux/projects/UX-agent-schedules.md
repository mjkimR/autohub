---
id: UX-agent-schedules
title: Project Agent Schedules
summary: "Configure project-owned provider-session schedules and request an enabled schedule for the next dispatcher tick."
area: projects
element: modal
status: active
usecases:
  - UC-run-agent-session
capabilities:
  - CAP-AGENT-provider-sessions
  - CAP-EXEC-scheduling-maintenance
---

# [UX-agent-schedules] Project Agent Schedules

## 1. Purpose

- **Primary task**: configure or queue a provider-session Schedule configuration.
- **Facts to commit**: project, supported AI catalog, work type, prompt, starting branch, enabled state and interval/cron trigger.
- **Secondary items**: recent Provider session summaries stay under their schedule; the full catalog session history is a separate catalog surface.

## 2. Content

The schedule list is primary. New/Edit opens an inline form within this modal, replacing its footer until saved or canceled.

- Schedule configuration (owned row): title, task/report type, enabled state, trigger, next due time and last-run time.
  - Provider session (recent summary): timestamp, provider state, PR link and shortened result summary when present.
- AI catalog (supported selector) and Schedule configuration (editor): title, prompt, starting branch, trigger and enabled flag.
- Actions: Edit, Run now, confirmed Delete, New schedule and Close.

New schedule is unavailable without a GitHub connection or a catalog supporting sessions. A run-now acceptance means queued for the next tick, not completed work.

## 3. States

- **populated**: inspect schedules, edit them, queue enabled work or close.
- **empty**: no schedules; create one if supported catalogs and GitHub configuration exist, otherwise configure those prerequisites first.
- **loading**: schedule loading text; wait for the list.
- **editing**: form fields and Save/Cancel replace the ordinary footer.
- **error**: request errors are toasts; retry a request or save a schedule again when its owned entry is missing.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| New schedule / save | `UC-run-agent-session` 1, `UC-run-agent-session` 2 | populated, empty, editing | editing, populated |  | `CAP-AGENT-provider-sessions` | A successful save closes the form, toasts and reloads the schedule list. |
| Edit existing schedule | `UC-run-agent-session` 1a | populated | editing |  | `CAP-AGENT-provider-sessions` | The inline form is populated from the selected schedule. |
| Run now | `UC-run-agent-session` 3 | populated | populated |  | `CAP-AGENT-provider-sessions` | A toast says queued for the next dispatcher tick and next-run data reloads. |
| Inspect schedule/request refusal | `UC-run-agent-session` 2a, `UC-run-agent-session` 3a, `UC-run-agent-session` 3b, `UC-run-agent-session` *a | editing, populated | error |  | `CAP-AGENT-provider-sessions` | The server error appears as a toast without a claimed schedule mutation or run. |
| Delete and confirm | global: remove the selected schedule and its derived scheduler entry | populated | populated, empty |  | `CAP-AGENT-provider-sessions` | Browser confirmation precedes deletion; success or refusal is reported by toast. |
| Cancel editor | global: return from schedule editing to its list | editing | populated |  | `CAP-AGENT-provider-sessions` | Unsaved form editing ends. |
| Close / dismiss | global: return to the project view | populated, empty, editing, error | populated | close |  | The project remains available. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/agent-schedules/AgentSchedulesDialog.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
