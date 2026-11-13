---
id: UX-agent-schedules
title: Project Agent Schedules
summary: "Configure project-owned provider-session schedules inline in the project's Automation section, queue an enabled schedule for the next dispatcher tick and open each recent session's PR run."
area: projects
element: panel
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
- **Facts to commit**: project, supported AI catalog, work type, prompt, starting branch, enabled state and
  interval/cron trigger.
- **Secondary items**: recent Provider session summaries stay under their schedule; the full catalog session history
  is a separate catalog surface.

## 2. Content

The region is the last section of the Automation section of `UX-project-detail`. The schedule list is primary.
New schedule and Edit replace the list with an inline form until it is saved or canceled.

- Schedule configuration (owned row): title, work type and enabled badges, trigger, next due time (while enabled) and
  last-run time; Run now, Edit and confirmed Delete name the schedule for assistive technology.
  - Provider session (recent summary): timestamp, provider state in display case, a `PR run` link to the run page
    (`/projects/{projectId}/runs/{runId}`, `UX-run-page`) when the session has an adopted PR run, `PR run history
    expired` when that run was retired, the PR link and a shortened result summary when present.
- AI catalog (supported selector) and Schedule configuration (editor): title, prompt, starting branch, trigger and
  enabled flag.

New schedule is unavailable without a GitHub connection or a catalog supporting sessions. A run-now acceptance means
queued for the next tick, not completed work.

## 3. States

- **populated**: inspect schedules, edit them, queue enabled work or open a recent session's PR run.
- **empty**: no schedules; create one if supported catalogs and GitHub configuration exist, otherwise the text names
  the missing prerequisite.
- **loading**: schedule loading status text; wait for the list.
- **editing**: the inline form with Save and Cancel replaces the list and New schedule.
- **error**: a failed list load shows Retry; request errors are toasts; retry a request or save a schedule again
  when its owned entry is missing.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| New schedule / save | `UC-run-agent-session` 1, `UC-run-agent-session` 2 | populated, empty, editing | editing, populated |  | `CAP-AGENT-provider-sessions` | A successful save closes the form, toasts and reloads the schedule list. |
| Edit existing schedule | `UC-run-agent-session` 1a | populated | editing |  | `CAP-AGENT-provider-sessions` | The inline form is populated from the selected schedule. |
| Run now | `UC-run-agent-session` 3 | populated | populated |  | `CAP-AGENT-provider-sessions` | A toast says queued for the next dispatcher tick and next-run data reloads. |
| Inspect schedule/request refusal | `UC-run-agent-session` 2a, `UC-run-agent-session` 3a, `UC-run-agent-session` 3b, `UC-run-agent-session` *a | editing, populated | error |  | `CAP-AGENT-provider-sessions` | The server error appears as a toast without a claimed schedule mutation or run. |
| PR run (recent session) | `UC-run-agent-session` 7 | populated | populated | `UX-run-page` | `CAP-AGENT-provider-sessions` | The PR run page of this project opens. |
| Delete and confirm | global: remove the selected schedule and its derived scheduler entry | populated | populated, empty |  | `CAP-AGENT-provider-sessions` | Browser confirmation precedes deletion; success or refusal is reported by toast. |
| Cancel editor | global: return from schedule editing to its list | editing | populated |  | `CAP-AGENT-provider-sessions` | Unsaved form editing ends. |
| Leave the section | global: move to another project section | populated, empty, editing, error | populated | `UX-project-detail` |  | The selected project section replaces the region. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/agent-schedules/AgentSchedulesPanel.svelte`
- `modules/hub-ui/src/lib/features/project-management/agent-schedules/AgentScheduleForm.svelte`

Inspected check: `AgentSchedulesPanel.integration.test.ts` covers the inline list, the recent session's PR run link,
creation from session-capable catalogs, inline edit, run-now, refusals and list retry. The content and transitions
are derived from source inspection. This document does not assert live provider verification.
