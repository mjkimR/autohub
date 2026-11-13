---
id: PROP-schedule-config-ownership-target
title: Schedule configuration ownership Living Spec targets
summary: "Draft schedule ownership read contract, project filter and owner-aware screen changes for the generic list and project Automation region."
status: draft
proposal: PROP-schedule-config-ownership
created_at: 2026-11-13
targets:
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
  - file: docs/capabilities/agents/CAP-AGENT-provider-sessions.md
  - file: docs/capabilities/projects/CAP-PROJ-project-connections.md
  - file: docs/ux/execution/UX-schedule-configs.md
  - file: docs/ux/projects/UX-project-detail.md
  - file: docs/steering/ux-objects.md
---

# [PROP-schedule-config-ownership-target] Schedule ownership Living Spec targets

This draft belongs to `PROP-schedule-config-ownership`. It describes intended documents after Development;
current Living Spec files are unchanged. Visual treatment follows `docs/steering/visual-style.md`.

## Contract ledger

| Existing document | Intended change | Acceptance |
| --- | --- | --- |
| `CAP-EXEC-scheduling-maintenance` | Define read-only owner projection, nullable unresolved IDs, generic mutation flag, pre-pagination `project_id` filter, consistent list/detail/mutation responses and bounded one-session reads. Preserve maintenance protection and scheduling behavior. | OWNER-01, OWNER-02, OWNER-03, OWNER-06 |
| `CAP-AGENT-provider-sessions` | State that configuration reads resolve the agent-schedule owner and keep generic mutation refused; operator synchronization configurations remain operator-owned. Existing schedule API and session execution stay unchanged. | OWNER-01, OWNER-04 |
| `CAP-PROJ-project-connections` | State that schedule reads expose project dispatch/observation ownership; dispatch protection remains distinct from editable observation configurations. | OWNER-01, OWNER-04 |
| `UX-schedule-configs` | Replace task-name owner guesses with verified owner links/action metadata and add the Project filter, unresolved-owner and filter-options failure states. | OWNER-04, OWNER-07 |
| `UX-project-detail` | Automation loads owned configurations using a project-filtered request and partitions by owner kind. Existing agent panel remains independently loaded. | OWNER-05 |
| `UX-agent-schedules` | No element-content change required: generic owner links enter this existing panel through Automation. Inspect links against the existing panel during reconciliation. | OWNER-04 |

No architecture document changes are expected: the existing layered ownership and one-request session remain intact.
The single PADR is promoted during handoff; its lasting read-contract clauses are restated in
`CAP-EXEC-scheduling-maintenance`. Generic schedule administration remains global navigation outside
`UC-run-due-work`, whose actor is the external scheduler. No external-scheduler step is repurposed as a UI goal.
`UC-run-agent-session` and `UC-configure-project-connection` keep their existing flow and screens.

## Screens

### `UX-schedule-configs` — retained screen with owner facts and project filtering

- element: screen
- usecases: [] (schedule administration is outside the external-scheduler goal)
- capabilities: `CAP-EXEC-scheduling-maintenance`, `CAP-PROJ-project-connections`, `CAP-AGENT-provider-sessions`

#### Purpose

Inspect Schedule configurations and act through the correct owner. The facts needed are task, trigger, enabled
state, next-run time, verified owner and whether the generic screen permits mutation. Editor, deletion confirmation
and manual dispatch remain existing secondary flows. The existing table stays the primary region; no arrangement
alternative is needed because the change enriches its rows and existing filter strip.

#### Content

The filter strip stays above the schedule table. Project is a labeled selector with `All projects` as the default,
loaded through the existing paginated project API pattern. It composes with search and All statuses/Active/Paused.

- Schedule configuration (table row): existing name, description, task, cadence, enabled and next-run facts.
  - Owner (secondary fact): `System Managed`, `Project Managed` or ordinary operator ownership, based on the server
    projection, never a provider-task-name guess.
  - Project connection (verified identity): show its resolved project name beside the row and include that name in
    the owner link accessible name. When project options cannot supply the name, use the verified project ID,
    so similarly named schedules from different projects remain distinguishable before navigation.
  - Project connection (owner action): `Project automation` for resolved dispatch/observation; `Agent schedules` for
    resolved agent ownership opens Automation, containing `UX-agent-schedules`; `Project connections` for a resolved
    retained Connection test opens Connections.
  - Unresolved protected owner (secondary fact): `Owner unavailable`; no guessed owner link or mutation action.
  - Allowed generic actions: Pause/Resume, Edit and Delete only when `generic_mutation_allowed=true`.
- Project connection (filter selector): project name; `All projects` clears only the project selection.
- Task specification (editor data): independent existing load/error and retry region.

#### States

- **loading**: schedule progress is announced; wait or change filters. Existing rows during refresh remain busy.
- **populated**: inspect verified owner facts, follow an owner link or use permitted generic actions.
- **empty**: no configurations match; clear/change filters or create an ordinary configuration.
- **error**: schedule-list loading shows Retry. Mutation errors toast without claiming a successful change.
- **project-options-error**: a separate message with Retry reports project-options failure; the unfiltered list and
  other filters remain available. Preserve any selected project value so failure cannot silently widen the list.
- **triggering**: the dispatch control is busy until the result; wait for claimed-count feedback.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Select/clear Project, search, status or page | global: schedule administration has no external-scheduler step | populated, empty, error | loading | | `CAP-EXEC-scheduling-maintenance` | Project/search/status changes reset to page one; matching rows/count reload and failures show Retry. |
| Retry project options | global: recover a filter's data | project-options-error | populated | | `CAP-EXEC-scheduling-maintenance` | Successful options reload restores the selector; repeated failure stays explicit. |
| Open resolved dispatch/observation owner | global: inspect the source project of a Schedule configuration | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The exact project's Automation tab opens. |
| Open resolved agent owner | global: manage a Schedule configuration at its owning agent schedule panel | populated | populated | `UX-project-detail` | `CAP-AGENT-provider-sessions` | The exact project's Automation tab opens containing `UX-agent-schedules`; exact row selection is outside scope. |
| Open resolved Connection test owner | global: inspect the owner of a retained Schedule configuration | populated | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The exact project's Connections tab opens. |
| New Schedule/Edit allowed row | global: schedule administration | populated, empty | populated | `UX-schedule-editor` | `CAP-EXEC-scheduling-maintenance` | Creation or the selected configuration's form opens. |
| Toggle allowed row | global: schedule administration | populated | populated | | `CAP-EXEC-scheduling-maintenance` | Success/error toast; success reloads, including owner/action facts. |
| Delete allowed row | global: schedule administration | populated | populated | `UX-schedule-delete` | `CAP-EXEC-scheduling-maintenance` | The named schedule is confirmed before irreversible deletion. |
| Trigger Dispatcher | global: schedule administration | populated | triggering | | `CAP-EXEC-scheduling-maintenance` | Existing toast reports claimed count; it does not claim task completion. |
| Navigate through console | global: leave schedule administration | populated, empty, error | populated | `UX-dashboard` | | Navigation replaces the table. |

#### Evidence

Existing `UX-schedule-configs` and `ScheduleConfigsView.svelte` supply the retained arrangement. Planned UI checks
cover OWNER-04 and OWNER-07; no screenshot or live browser evidence was produced in Planning.

### `UX-project-detail` — Automation owned-schedule region

- element: screen (the retained Project detail screen; draft is limited to its Automation owned-schedule region)
- usecases: retain all existing use cases and interactions of `UX-project-detail`
- capabilities: retain existing relationships, including `CAP-PROJ-project-connections`

#### Purpose

Inspect the current Project connection's automation and edit its permitted schedules. The existing Automation
sections retain their hierarchy; navigation to other Project detail tabs and the project list is the screen exit.

#### Content

- Project connection (Automation configuration): existing dispatch interval and policy controls.
- Schedule configuration (owned list): dispatch, CI observation and retained Connection test groups selected from
  the server's project-filtered response using owner kind. Existing cadence, next-run facts and actions stay in place.
- Agent schedule region: existing `UX-agent-schedules`, loaded from its dedicated project API without duplication.

#### States

- **loading**: owned-schedule progress text; wait or switch tab.
- **populated**: inspect schedules and use existing allowed actions.
- **empty**: existing group explanations remain; add CI observation where permitted or follow Connections.
- **error**: Retry the project-filtered request; a failed read is distinguishable from no owned schedules.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open Automation or retry owned schedules | global: inspect schedules belonging to the current Project connection | populated, error | loading | | `CAP-PROJ-project-connections` | Only this project's schedules reload, without a cross-project scan or separate Connection test read. |
| Create/edit CI observation | global: maintain this project's observation schedule | populated, empty | populated | `UX-project-schedule` | `CAP-PROJ-project-connections` | The existing editor opens and saved changes refresh the project-filtered list. |
| Open agent schedule region | global: enter the existing provider-schedule management panel | populated | populated | `UX-agent-schedules` | `CAP-AGENT-provider-sessions` | Existing agent schedule controls remain available. |
| Open Connections or leave Automation | global: inspect connection tests or another project section | populated, empty, error | populated | `UX-project-detail` | `CAP-PROJ-project-connections` | The chosen project tab replaces Automation. |
| Back to Projects | global: leave the current Project connection | populated, empty, error | populated | `UX-projects` | | The project list opens. |

All other content, states, use-case steps and interactions remain the existing `UX-project-detail` contract.
No new use-case step is inferred from changing the data source. Planned UI checks cover OWNER-05.

## UX object register delta

The Schedule configuration / Operator row gains `verified owner fact/link` representation and `Open owner` call to
action. The Project connection / Operator row's existing open/edit representation covers the Project selector and
owner links. No domain term changes are required. Apply this one row addition to `docs/steering/ux-objects.md` during
reconciliation; do not duplicate glossary definitions in this draft.
