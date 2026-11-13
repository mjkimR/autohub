---
id: PROP-hub-ui-shell-polish
title: Shell counts error reason and sidebar scroll cue
summary: "Keep the reason a shared owed-counts read failed so the Projects Needs-you tooltip can name it, and show a scroll cue when the sidebar navigation overflows."
status: reviewing                     # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: ux/navigation/
priority: low                         # critical | high | medium | low
size: S                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: low                  # low | medium | high (hint for Planning)
dev_effort: low                       # low | medium | high (hint for Development)
boundaries:
  owns:
    - ux/navigation/
    - ux/projects/
    - modules/hub-ui/src/lib/features/attention/
    - modules/hub-ui/src/lib/features/project-management/projects/
    - modules/hub-ui/src/lib/components/shared/
  excludes:
    - docs/decisions/
    - modules/hub/
    - modules/hub-ui/src/lib/api/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-hub-ui-shell-polish] Shell counts error reason and sidebar scroll cue

## 1. Background & Hypothesis

Two small shell gaps remained after the 2026-11-13 UX program (`SPEC-owed-item-contract` and the Attention landing,
`UX-attention`):

- **(a) Counts error reason**: the shared owed-counts store
  (`modules/hub-ui/src/lib/features/attention/owed-counts.svelte.ts`) models a failed read as
  `{ status: 'unknown' }`, the same value as loading, and keeps no message. `OwedCountsStore.refresh` ignores the
  response `error` (it passes only `data` to `summarizeOwedCounts`) and swallows exceptions. `ProjectsView.svelte`
  (`modules/hub-ui/src/lib/features/project-management/projects/`) therefore sets `needsYouError` to empty whenever
  the shell store exists, so the Needs-you `—` cell has no tooltip. Only the out-of-shell fallback read names a reason
  ("Needs-you count unavailable: <message>"), and only that path is tested
  (`ProjectsView.integration.test.ts`, "Needs-you count unavailable: Database busy"). `UX-projects` states without
  qualification that "a failed read names its reason in the tooltip", which the deployed app, always inside the
  shell, does not do. The shell's own "?" mark (`AppShell.svelte`) carries only `OWED_UNKNOWN_LABEL` ("Owed items
  unknown").
- **(b) Sidebar scroll cue**: the primary navigation in `modules/hub-ui/src/lib/components/shared/AppShell.svelte` is
  `<nav class="flex-1 space-y-5 overflow-y-auto py-4">` between the brand and the bottom status area, with four groups
  (Attention, Work, Setup and System, which has six links; `app-shell-nav.ts`) plus Administration for admins. When it overflows on a short viewport, nothing shows
  that more links sit below or above; `SidebarLink.svelte` only scrolls the active link into view
  (`scrollIntoView({ block: 'nearest' })`), which `UX-app-shell` states ("When the sidebar list overflows, the active
  link is scrolled into view"). No overflow cue is documented or implemented.

Hypothesis: a store that distinguishes loading from failure and keeps the failure message, and an edge cue on the
overflowing navigation, close both gaps without new reads or layout changes.

## 2. Technical Spike Questions

- **Q1 (store shape)**: Does `OwedCounts` gain a separate `error` status with a message, or does `unknown` carry an
  optional reason? Both the shell "?" mark and the Attention landing read the same value; does either show the reason,
  or only the Projects tooltip?
- **Q2 (message source)**: Is the reason `apiErrorMessage` of the response error, with a fixed fallback for network
  failures and invalid responses, so no server detail beyond the existing API error message reaches the tooltip?
- **Q3 (cue form)**: Is the cue a fade or shadow at the overflowing edge driven by scroll position, built from theme
  tokens in `src/routes/layout.css` without raw palette colors, and is it hidden from assistive technology?
- **Q4 (classification)**: `UX-projects` already promises the reason, so (a) can be read as a defect against that
  contract (task kind `bugfix`) while (b) is a feature. Is (a) treated as completing the shared-store design within this
  feature, or split into its own bugfix?

## 3. Proposed Design & Impact

Direction, to be settled in Planning:

1. `OwedCountsStore` records the last failure's message, keeps a loading state distinct from failure, and keeps the
   neutral display rule (an outage never reads as zero or debt). `ProjectsView.svelte` uses the store's reason for the
   `—` tooltip, so in-shell and fallback paths behave the same; tests cover the in-shell failure tooltip.
2. The sidebar navigation shows a top and bottom cue while content is scrolled past that edge, and none when nothing
   overflows; `AppShell.integration.test.ts` covers both.

Expected impact: `owed-counts.svelte.ts` and its tests, `ProjectsView.svelte`, `AppShell.svelte` or a small sidebar
component, `UX-app-shell` (overflow cue) and `UX-projects` (evidence for the in-shell tooltip). No API or backend change.

Placement: neither part belongs in `PROP-run-origin-links` (subject links) or `PROP-schedule-config-ownership`
(schedule owners); both are shell-level signals with no shared code path with those proposals.

Size: `S`, two independent, self-contained fixes. If Q4 settles (a) as a bugfix, the mixed task kinds would make this
draft `XL` by definition, and it should split into two `S` drafts rather than change size.

Non-goals:

1. Changing the counts poll cadence, throttle or the read itself.
2. Redesigning the sidebar groups, their order or the collapsed diagnostic groups.
3. Showing counts error reasons anywhere other than where a count is unavailable.

## 4. Lifecycle & Retirement Criteria
<!--
- Preliminary decisions: devkit spec proposal padr hub-ui-shell-polish "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept hub-ui-shell-polish --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff hub-ui-shell-polish.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->
