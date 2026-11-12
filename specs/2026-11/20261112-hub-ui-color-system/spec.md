---
id: SPEC-hub-ui-color-system
title: Rank operator attention in the hub-ui color system
summary: "Replace the blue-led hub-ui palette with ink actions, neutral surfaces and an amber attention token so that only work waiting for the operator and failures carry saturated color."
status: planned
created: 2026-11-12
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---

# [SPEC-hub-ui-color-system] Rank operator attention in the hub-ui color system

## 1. Problem Statement & Motivation

The hub-ui palette spends its strongest hue on routine elements. The light `--primary` (oklch 0.488 0.243 264) has
more chroma than every status color except `--destructive`, and it fills 71 default buttons, decorative icon tiles,
section-header icons, the login backdrop and the favicon. Blue chroma also tints `--secondary`, `--accent`,
`--sidebar-accent` and every dark surface, and `--info` sits within 30 degrees of `--primary`, so routine progress
reads as an action.

Exception states are not ranked. A paused PR run uses the same `warning` badge as a run routinely awaiting CI; a
blocked run uses the same `destructive` badge as a failed one. The dashboard gives Active Work, Awaiting CI, Completed
and "Needs you" equal tinted tiles, and "Needs you" borrows failure red for an intervention signal. The Decisions inbox
shows "Needs decision" as plain text, and its only colored element is the blue Review button. An operator scanning
the console cannot tell, by emphasis, which items are waiting for them.

The approved direction is that saturated color marks operator debt. Actions and surfaces are ink and neutral grey.
One amber `attention` token family marks work waiting for the operator. Red marks failures and destructive actions.
Success, info and warning become quiet, low-chroma signals. Each status keeps a text label and gains a distinct icon,
so no state is conveyed by color alone.

### Source anchors

- Tokens: `modules/hub-ui/src/routes/layout.css`; badge variants: `modules/hub-ui/src/lib/components/ui/badge/badge.svelte`.
- Run state mapping: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.ts`, consumed by
  `PipelineRunRow.svelte`, `RunDecisionsDialog.svelte`, `repositories/SddRunLinks.svelte` and
  `features/dashboard/DashboardView.svelte`.
- Dashboard tiles: `DashboardView.svelte`; the "Needs you" count is `dashboard.failedRuns` (failed + paused + blocked,
  or the unknown marker `—`) in `features/dashboard/dashboard.svelte.ts`.
- Decisions inbox row: `pipeline-runs/DecisionInbox.svelte`.
- Design-system lint contracts: `modules/hub-ui/README.md` (Design-system lint) and `modules/hub-ui/eslint.config.js`.

## 2. User Stories

- **US-1**: As an operator, I want work waiting for me (paused or blocked runs, pending decisions) to be the only
  amber element on a screen, so that I find it without reading every row.
- **US-2**: As an operator, I want failures to stay red and distinct from runs that need my intervention, so that I
  can tell a broken run from a held one.
- **US-3**: As an operator, I want routine progress and completed work to stay visually quiet, so that they do not
  compete with exceptions.
- **US-4**: As an operator using a screen reader, a monochrome display or either theme, I want every status to carry
  a text label and an icon, so that no status depends on hue.
- **US-5**: As a hub-ui contributor, I want an `attention` token and Badge variant documented beside the other status
  colors, so that new screens apply the same ranking without raw palette classes.

No use case goal changes. The listed screens keep their content, states and interactions except for the
representations in the Screens section, so `related_usecases` stays empty.

## 3. Non-Goals

1. **Scope Excluded**: Shell lighting, meaning an amber rule at the top of the application shell or a pending-count
   badge on the Decisions navigation item.
   **When to Reconsider**: when a global pending-decision count source exists for the shell.
2. **Scope Excluded**: Any backend, API, OpenAPI schema or generated-client change. Every state and count shown is
   already delivered by the current API.
3. **Scope Excluded**: Layout or information-architecture changes beyond the elements listed in this spec: no region
   moves, no new screens, no new navigation and no changed interactions.
4. **Scope Excluded**: Typography, font, radius and spacing changes.
5. **Scope Excluded**: Recoloring elements not listed here. Elements that use `primary` (default buttons, links,
   checkboxes, selected toggles, active tabs, focus rings) change only through the new token values; their classes
   stay.
6. **Scope Excluded**: Charts. `--chart-1` to `--chart-5` stay greyscale and unused.

## 4. Acceptance Criteria & Behavioral Contracts

Token values are OKLCH. "Key pairs" are the pairs listed in AC-06. Run labels are the run state with underscores
replaced by spaces (`awaiting ci`), as rendered today.

### [AC-01] Ink primary and neutral surfaces

- **Given** `modules/hub-ui/src/routes/layout.css`
- **When** its `:root` and `.dark` custom properties are read
- **Then** light `--primary` is `oklch(0.24 0.012 260)` with `--primary-foreground` `oklch(0.985 0 0)`, and dark
  `--primary` is `oklch(0.93 0.005 260)` with `--primary-foreground` `oklch(0.17 0.005 260)`
- **And** `--sidebar-primary` equals `--primary` in each theme, and `--ring` is `oklch(0.45 0.01 260)` light and
  `oklch(0.75 0.005 260)` dark
- **And** `--background`, `--card`, `--popover`, `--muted`, `--secondary`, `--accent`, `--sidebar` and
  `--sidebar-accent` have chroma `0` in both themes, with the values in the plan's token table
- **And** `--chart-1` to `--chart-5` keep chroma `0`.

### [AC-02] Attention token family and quiet status tokens

- **Given** `layout.css`
- **When** its custom properties and `@theme inline` block are read
- **Then** each theme defines `--attention`, `--attention-foreground`, `--attention-text` and `--attention-surface`,
  and `@theme inline` registers `--color-attention`, `--color-attention-foreground`, `--color-attention-text` and
  `--color-attention-surface`
- **And** light values are `0.78 0.165 70`, `0.20 0.04 55`, `0.50 0.13 55`, `0.97 0.04 80`; dark values are
  `0.82 0.16 75`, `0.19 0.04 55`, `0.82 0.16 75`, `0.24 0.05 70`
- **And** `--success`, `--info` and `--warning` have chroma at most `0.08` in both themes, and `--destructive` is
  `oklch(0.53 0.19 27)` light and `oklch(0.68 0.17 25)` dark.

### [AC-03] Attention Badge variant

- **Given** `modules/hub-ui/src/lib/components/ui/badge/badge.svelte`
- **When** a Badge renders with `variant="attention"`
- **Then** it uses only `attention*` tokens for its border, background and text, and `BadgeVariant` accepts
  `'attention'`
- **And** existing variants keep their names and class strings.

### [AC-04] Run state ranking

- **Given** a PR run badge rendered by the dashboard recent list, Pipeline Runs row, run decisions dialog or SDD run
  links
- **When** the run state is each value of `PipelineRunState`
- **Then** the badge variant and icon are:

  | State | Variant | Icon (`@lucide/svelte`) |
  | --- | --- | --- |
  | queued | outline | CircleDashed |
  | dispatching | info | Loader |
  | implementing | info | Loader |
  | awaiting_ci | outline | Clock |
  | completed | success | Check |
  | canceled | secondary | Slash |
  | paused | attention | Pause |
  | blocked | attention | Ban |
  | failed | destructive | OctagonX |

- **And** every badge shows its text label next to the icon, and the icon is `aria-hidden`
- **And** no run state maps to `warning`, and the four call sites render the same component, so their variant, icon
  and label agree
- **And** a unit test covers all nine states.

### [AC-05] Dashboard PR run summary

- **Given** the dashboard PR run summary with counts loaded
- **When** the Needs-you count (failed + paused + blocked) is greater than `0`
- **Then** the "Needs you" tile is the only tile with a colored fill, using `attention` with `attention-foreground`
  text, and shows the count
- **And** Total Runs, Active Work, Awaiting CI and Completed tiles use the same neutral card styling with no status
  color on border, fill or number
- **When** the Needs-you count is `0`
- **Then** the tile is neutral like the others and shows the text "Nothing waiting"
- **When** statistics are unavailable (`—`)
- **Then** the tile is neutral and shows the unknown marker
- **And** the integration test asserts the `> 0`, `0` and unknown cases by text, and the colored case by a stable
  attribute (for example `data-attention="true"`), not by class names.

### [AC-06] Contrast of key pairs

- **Given** the token values in both themes
- **When** WCAG 2.x relative-luminance contrast is computed from the OKLCH values converted to sRGB, with alpha
  tints composited over the surface they sit on
- **Then** each text pair is at least `4.5:1`: foreground and muted-foreground on background, card and muted;
  primary-foreground on primary; attention-foreground on attention; attention-text on background, card and
  attention-surface; success, info, warning and destructive on card and on their own Badge tint over card and over
  background
- **And** each UI component pair is at least `3:1`: ring on background, primary on background, and the attention
  stroke (left rule and chip dot) on card and background
- **And** a committed unit test parses `layout.css`, computes these pairs and fails when one falls below its
  threshold, so the check runs in `just test-ui`.

### [AC-07] Decisions inbox row status

- **Given** the Decisions inbox with loaded rows
- **When** a row is actionable and its question state is not `answered`
- **Then** the row shows an `attention` Badge with a dot and the label "Needs decision", and the row has a 3px left
  rule in the attention stroke color; the row background stays neutral
- **When** a row's question state is `answered`
- **Then** it shows a `success` Badge with a Check icon and the label "Answer saved", and no left rule
- **When** a row is not actionable
- **Then** it shows an `info` Badge with a Clock icon and the label "Answer publication pending", and no left rule
- **And** the per-row Review button, Retry and Retry review use the `outline` variant
- **And** the integration test asserts each label and the left-rule marker by text or a stable attribute.

### [AC-08] Decorative primary removed

- **Given** authored hub-ui source outside `src/lib/components/ui/`
- **When** it is searched after the change
- **Then** the "Svelte 5 Runes" chip in the application shell header is gone
- **And** no element uses `bg-primary/10` as a decorative icon tile, chip or backdrop; icon tiles use `bg-muted` with
  `text-muted-foreground`
- **And** the section-header icons in `DashboardView.svelte`, `JsonSchemaForm.svelte`, `AttemptHistoryDialog.svelte`
  and `ProjectConnectionCheckDialog.svelte` use `text-muted-foreground`
- **And** `hover:border-primary` no longer appears; hover borders use a neutral token
- **And** the login screen has no colored blur backdrop and its logo tile has no `shadow-primary` glow
- **And** `src/app.html` text selection uses neutral tokens
- **And** `src/lib/assets/favicon.svg` contains no `#6366f1`; its stroke is ink `#1c1f25`, switching to `#e6e8eb`
  under `prefers-color-scheme: dark`.

### [AC-09] Schedule job statuses use tokens

- **Given** `ScheduleJobsView.svelte`
- **When** a Schedule job status is `success`, `failure`, `pending` or another value
- **Then** it renders a Badge with variant `success`, `destructive`, `outline` or `secondary`, keeping its current
  icon and label
- **And** no `emerald` or `amber` class remains in authored hub-ui source.

### [AC-10] Lint and checks

- **Given** the finished change
- **When** `just lint`, `just check` and `just test-ui` run from the repository root
- **Then** each exits `0`
- **And** `npx eslint` on every touched authored file reports `0` `shadcn/*` warnings
- **And** no size-preset ceiling in `modules/hub-ui/eslint.config.js` is raised or added.

### [AC-11] Use cases stay achievable

- **Given** the use cases cited by `UX-decision-inbox`, `UX-pipeline-runs`, `UX-dashboard` and `UX-app-shell`
  (`UC-receive-decision-notice`, `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`,
  `UC-deliver-pull-request`, `UC-access-hub`)
- **When** the existing integration tests for those screens run
- **Then** they pass with only label, representation or attribute updates, and no Interactions row of those UX
  documents loses its trigger or target.

## 5. Screens

The changed elements are three existing screens and one shared representation. Each draft lists only what changes;
unchanged Purpose, regions, states and Interactions rows stay as in the current UX document. Emphasis is written as a
role (attention, failure, quiet, neutral); the visual style steering file the plan adds owns the token mapping.

### Candidates and recommendation

The arrangement is fixed by the approved direction: no region moves. The open choice was where attention appears.

- **Recommended — marks on existing elements**: attention appears only on badges, the Needs-you tile and the inbox
  row's left rule. It adds no region and keeps every screen's primary region.
- **Rejected — shell lighting**: an amber shell rule and a Decisions navigation count. It needs a global
  pending-count source (Non-Goal 1).
- **Rejected — full-row amber backgrounds**: it raises alarm fatigue and lowers text contrast on dense lists.

### UX-dashboard — System overview screen (changed region)

- **Primary task**: unchanged.
- **Content change**: PR run (summary counts) shows Total Runs, Active Work, Awaiting CI and Completed as neutral
  counts of equal weight, and a Needs-you count (failed, paused or blocked PR runs). The Needs-you count is the only
  emphasized tile: attention emphasis with its count when it is above zero; neutral with the label "Nothing waiting"
  at zero; neutral with the unknown marker when statistics cannot be loaded.
- **Content change**: PR run (recent list) state uses the PR run state badge below.
- **States**: **populated** gains the distinction above; **loading** and **degraded** keep the unknown marker on a
  neutral tile; next actions are unchanged (Refresh, Retry, navigation).
- **Interactions**: unchanged; the summary tiles remain non-interactive.

### UX-decision-inbox — Decision inbox (changed row)

- **Primary task**: unchanged.
- **Content change**: each PR run row's decision status is a labeled badge:
  - "Needs decision" (attention emphasis, dot) when the row is actionable and unanswered; the row also carries an
    attention left rule so pending rows can be found by scanning the list edge.
  - "Answer saved" (quiet success, check icon) when the Run question is answered.
  - "Answer publication pending" (quiet info, clock icon) while the Native SDD activity is not actionable.
- **Content change**: Review, Retry and Retry review are secondary-weight (outline) buttons, so the status badge,
  not the button, carries the row's emphasis.
- **States**: unchanged; **empty**, **error** and **loading** show no attention marks.
- **Interactions**: unchanged. Review still serves `UC-resolve-run-question` 1, `UC-decide-sdd-proposal` 1,
  `UC-complete-sdd-workflow` 3b, 3c, 3d and 4; Retry review still serves `UC-receive-decision-notice` 2b.

### UX-pipeline-runs — Pipeline Runs (changed representation)

- **Primary task**: unchanged.
- **Content change**: PR run (row) state is the PR run state badge: label plus icon, ranked as failure (failed),
  attention (paused, blocked), quiet progress (dispatching, implementing), quiet success (completed) or neutral
  (queued, awaiting CI, canceled). The pause reason stays below the badge.
- **States**: unchanged. **operating** keeps the row's badge until the refreshed state arrives.
- **Interactions**: unchanged; Resume Run on a blocked or paused row still serves `UC-deliver-pull-request` *c.

### PR run state badge (shared representation)

The same badge appears in `UX-dashboard` (recent list), `UX-pipeline-runs` (row), `UX-run-decisions` (header) and
the SDD run links of `UX-sdd-execution`. It is a representation, not an element, so it gets no UX document. The
PR run row of `docs/steering/ux-objects.md` already names its "state/lease context" representation, so the register
is unchanged.

### UX review

The optional `ux-reviewer` walk-through is offered to the Host, which decides whether to run it before
implementation. It was not run while drafting.

## 6. Assumptions

- Review, Retry and Retry review become `outline` rather than staying `default` (ink). Repeated solid ink buttons
  on every inbox row would outweigh the attention badge.
- Light `--warning` is `oklch(0.50 0.08 80)`, not the drafted `0.52`: at `0.52` warning text on its Badge tint over
  `--background` measured `4.36:1`.
- In light mode `--attention` (`0.78 0.165 70`) measures `2.06:1` on `--card`, so strokes and dots that must meet
  `3:1` (inbox left rule, chip dot) use `--attention-text`, which measures `6.27:1`; filled areas carrying
  `--attention-foreground` text use `--attention`.
- Dispatching and implementing use a static Loader icon; the pulsing dot in `PipelineRunRow.svelte` is removed so
  motion does not compete with attention.
- Schedule job `pending` is routine and maps to `outline`, not `attention`.
- Selected and active states that use `primary` (dashboard polling toggle, project tabs, schedule cards) keep their
  classes and become ink through the token change.
- Contrast pairs were pre-computed from the drafted values with a WCAG relative-luminance script during
  specification; AC-06 makes the committed test the authoritative check.
