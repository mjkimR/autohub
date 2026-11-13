---
id: SPEC-hub-ui-color-system
title: Rank operator attention in the hub-ui color system
summary: "Replace the blue-led hub-ui palette with ink actions, neutral surfaces and an amber attention token so that only work waiting for the operator and failures carry saturated color."
status: in-progress
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
  can tell a broken run from a held one. The dashboard Needs-you tile groups every operator-actionable run; its
  per-state breakdown keeps failed runs distinguishable there.
- **US-3**: As an operator, I want routine progress and completed work to stay visually quiet, so that they do not
  compete with exceptions.
- **US-4**: As an operator using a screen reader, a monochrome display or either theme, I want every status to carry
  a text label and an icon, so that no status depends on hue.
- **US-5**: As a hub-ui contributor, I want an `attention` token and Badge variant documented beside the other status
  colors, so that new screens apply the same ranking without raw palette classes.

No use case goal changes, so `related_usecases` stays empty.

**Focus**: the change is centered on the color system and exception-signal ranking. Interaction and structural
changes that serve this goal are allowed as long as every documented use case stays achievable (AC-11). The Screens
section lists each such change with its use case citations.

## 3. Non-Goals

1. **Scope Excluded**: Shell lighting, meaning an amber rule at the top of the application shell or a pending-count
   badge on the Decisions navigation item, and any global pending-decision count.
   **When to Reconsider**: when a global pending-decision count source exists for the shell.
2. **Scope Excluded**: Any backend, API, OpenAPI schema or generated-client change. Every state and count shown is
   already delivered by the current API.
3. **Scope Excluded**: Typography and font changes.
4. **Scope Excluded**: Charts. `--chart-1` to `--chart-5` stay greyscale and unused.

## 4. Acceptance Criteria & Behavioral Contracts

Token values are OKLCH. "Key pairs" are the pairs listed in AC-06. Run labels are the display-case run state written
out in code (`Awaiting CI`, `Implementing`), not produced by CSS `capitalize`, so acronyms keep their case.

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
  | dispatching | info | Hammer |
  | implementing | info | Hammer |
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
- **And** its caption is the per-state breakdown of the non-zero counts in the order failed, paused, blocked,
  joined by ` · ` (for example `1 failed · 2 paused · 1 blocked`), computed client-side from `runs_by_state`
- **And** Total Runs, Active Work, Awaiting CI and Completed tiles use the same neutral card styling with no status
  color on border, fill or number
- **When** the Needs-you count is `0`
- **Then** the tile is neutral like the others, shows the text "No failed or held runs" in place of the count, and
  keeps the caption "Failed, paused, or blocked"
- **When** statistics are unavailable (`—`)
- **Then** the tile is neutral, shows the unknown marker and keeps the caption "Failed, paused, or blocked"
- **And** the label "Nothing waiting" is not used, because the tile does not count pending decisions (Non-Goal 1)
- **And** the integration test asserts the `> 0` (count and breakdown), `0` and unknown cases by text, and the
  colored case by `data-attention="true"`, not by class names.

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

The inbox uses exactly these status labels; spec-sync copies them into `UX-decision-inbox`.

| Row condition | Badge variant | Icon | Label | Attention left rule |
| --- | --- | --- | --- | --- |
| actionable, question state not `answered` | attention | dot | Needs decision | yes |
| actionable, question state `answered` | attention | CornerDownRight | Answer saved — resume pending | yes |
| not actionable | info | Clock | Answer publication pending | no |

- **Given** the Decisions inbox with loaded rows
- **When** each row condition above holds
- **Then** the row shows the listed Badge, icon and label; the icon or dot is `aria-hidden`
- **And** a row with an attention left rule has a 3px left border in the attention stroke color and
  `data-attention="true"`; the row background stays neutral
- **And** the Question state filter options read "All states", "Needs decision" (`open`) and "Answer saved — resume
  pending" (`answered`); the option values are unchanged
- **And** `success` with Check is not used in the inbox list
- **And** the per-row Review button, Retry and Retry review use the `outline` variant
- **And** the integration test asserts each of the three labels and that `data-attention` is present only on the
  two attention rows.

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

### [AC-12] Needs-you tile opens Pipeline Runs

- **Given** the dashboard with a Needs-you count greater than `0`
- **When** the operator activates the Needs-you tile
- **Then** the tile is a link to `/projects/runs` with no query string, and Pipeline Runs opens with its default
  filters
- **And** the link's accessible name contains "Needs you" and the count
- **When** the count is `0` or unknown
- **Then** the tile is not a link
- **And** the integration test asserts the `href` when the count is above `0` and the absence of a link at `0`.

The link is unfiltered. `/projects/runs` reads only the `run` and `view` query parameters, and the
`GET /api/v1/pipeline-runs` `state` parameter accepts one `PipelineRunState`, so preselecting failed, paused and
blocked together would need an API change (Non-Goal 2).

### [AC-11] Use cases stay achievable

- **Given** the use cases cited by `UX-decision-inbox`, `UX-pipeline-runs`, `UX-dashboard` and `UX-app-shell`
  (`UC-receive-decision-notice`, `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`,
  `UC-deliver-pull-request`, `UC-access-hub`)
- **When** each step those documents' Interactions rows serve is traced through the changed screens
- **Then** every step still has a trigger on its cited screen that reaches the cited target
- **And** the existing integration tests for those screens pass, changed only where a label, representation,
  attribute or interaction listed in the Screens section changed.

## 5. Screens

The changed elements are three existing screens and one shared representation. Each draft lists what changes,
including interactions; anything not listed stays as in the current UX document. A changed interaction cites the
use case step it serves. Emphasis is written as a role (attention, failure, quiet, neutral); the visual style
steering file the plan adds owns the token mapping.

### Candidates and recommendation

The open choice was where attention appears.

- **Recommended — marks on existing elements**: attention appears only on badges, the Needs-you tile and the inbox
  row's left rule, and the Needs-you tile becomes the path to the runs it counts. It keeps every screen's primary
  region.
- **Rejected — shell lighting**: an amber shell rule and a Decisions navigation count. It needs a global
  pending-count source (Non-Goal 1).
- **Rejected — full-row amber backgrounds**: it raises alarm fatigue and lowers text contrast on dense lists.

### UX-dashboard — System overview screen (changed region)

- **Primary task**: unchanged.
- **Content change**: PR run (summary counts) shows Total Runs, Active Work, Awaiting CI and Completed as neutral
  counts of equal weight, and a Needs-you count (failed, paused or blocked PR runs). The Needs-you tile is the only
  emphasized tile:
  - above zero: attention emphasis, the count, a breakdown caption such as "1 failed · 2 paused · 1 blocked", and a
    link to `UX-pipeline-runs`;
  - zero: neutral, "No failed or held runs", caption "Failed, paused, or blocked", not a link;
  - statistics unavailable: neutral, the unknown marker, the same caption, not a link.
- **Content change**: PR run (recent list) state uses the PR run state badge below.
- **States**: **populated** gains the distinction above; **loading** and **degraded** keep the unknown marker on a
  neutral tile; next actions are unchanged (Refresh, Retry, navigation).
- **Interactions** (added row):

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open the Needs-you tile | global: navigation from the exception count to the runs it counts | populated | populated | `UX-pipeline-runs` | | Pipeline Runs opens with default filters; the operator filters by state and continues `UC-deliver-pull-request` *a, *b or *c there. |

### UX-decision-inbox — Decision inbox (changed row)

- **Primary task**: unchanged.
- **Content change**: each PR run row's decision status is one labeled badge, with the exact labels of AC-07:
  - "Needs decision" (attention emphasis, dot, attention left rule) when the row is actionable and unanswered.
  - "Answer saved — resume pending" (attention emphasis, corner-down-right icon, attention left rule) when the Run
    question is answered but the Run has not resumed; the operator still owes `UC-resolve-run-question` 4.
  - "Answer publication pending" (quiet info, clock icon, no rule) while the Native SDD activity is not actionable.
- **Content change**: the Question state filter options use the same labels: "Needs decision" and "Answer saved —
  resume pending". The document's earlier "Needs answer" becomes "Needs decision".
- **Content change**: Review, Retry and Retry review are secondary-weight (outline) buttons, so the status badge,
  not the button, carries the row's emphasis.
- **States**: unchanged; **empty**, **error** and **loading** show no attention marks.
- **Interactions**: existing rows stay; Review still serves `UC-resolve-run-question` 1, `UC-decide-sdd-proposal` 1,
  `UC-complete-sdd-workflow` 3b, 3c, 3d and 4, and Retry review still serves `UC-receive-decision-notice` 2b. Added
  row:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Review saved answer | `UC-resolve-run-question` 4 | populated | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | The exact question opens with its saved answer, ready to select for resume. |

### UX-pipeline-runs — Pipeline Runs (changed representation)

- **Primary task**: unchanged.
- **Content change**: PR run (row) state is the PR run state badge: label plus icon, ranked as failure (failed),
  attention (paused, blocked), quiet progress (dispatching, implementing), quiet success (completed) or neutral
  (queued, awaiting CI, canceled). The pause reason stays below the badge.
- **States**: unchanged. **operating** keeps the row's badge until the refreshed state arrives.
- **Interactions**: unchanged; it is the target of the dashboard's Needs-you tile. Resume Run on a paused or blocked
  row still serves `UC-deliver-pull-request` *c.

### PR run state badge (shared representation)

The same badge appears in `UX-dashboard` (recent list), `UX-pipeline-runs` (row), `UX-run-decisions` (header) and
the SDD run links of `UX-sdd-execution`. It is a representation, not an element, so it gets no UX document. The
PR run row of `docs/steering/ux-objects.md` already names its "state/lease context" representation, so the register
is unchanged.

### UX review

Round 1 of the `ux-reviewer` ran on the drafts at `1341b8d` and is recorded in `envelopes/ux-review-01.yaml`. This
revision folds its findings: Answer saved is attention work, the zero-count label claims only what it counts, the
Needs-you tile links to Pipeline Runs and shows a breakdown, the inbox labels are settled, and progress uses a
non-loading glyph. The deliberate-pause finding is accepted as designed (section 6), and the delta-draft coverage
finding needs no change.

## 6. Assumptions and Accepted Rationale

- **Accepted rationale**: deliberately paused runs stay attention. Resuming a paused run always needs the operator,
  so it is operator debt even when the pause was intended. No API change distinguishes intent.
- Review, Retry and Retry review become `outline` rather than staying `default` (ink); the ux-reviewer confirmed
  this. Repeated solid ink buttons on every inbox row would outweigh the attention badge.
- Light `--warning` is `oklch(0.50 0.08 80)`, not the drafted `0.52`: at `0.52` warning text on its Badge tint over
  `--background` measured `4.36:1`.
- In light mode `--attention` (`0.78 0.165 70`) measures `2.06:1` on `--card`, so strokes and dots that must meet
  `3:1` (inbox left rule, chip dot) use `--attention-text`, which measures `6.27:1`; filled areas carrying
  `--attention-foreground` text use `--attention`.
- Dispatching and implementing use a static Hammer icon (work in progress). A loader glyph reads as a stalled
  spinner when static, and Play or Cog would clash with the Resume control or settings. The pulsing dot in
  `PipelineRunRow.svelte` is removed so motion does not compete with attention.
- Schedule job `pending` is routine and maps to `outline`, not `attention`.
- Selected and active states that use `primary` (dashboard polling toggle, project tabs, schedule cards) keep their
  classes and become ink through the token change.
- The active sidebar item keeps its existing `aria-current`, `font-semibold` and foreground text contrast (about
  `15:1` against about `5.6:1` for inactive items); its `sidebar-accent` fill alone measures about `1.14:1`.
- Build-verify polish (Impeccable audit, in scope): the Resume and Pause controls on a Pipeline Runs row are ink with
  no status hue; run labels are explicit display-case strings ("Awaiting CI"); the retired "Scheduler Manager"
  subtitle under the shell's "Autohub" name is removed; the dashboard sync indicator drops `animate-pulse` and keeps
  its icon and text, so the Needs-you tile is the only salient element; and the dashboard activity cards gain
  `min-w-0`, which fixes horizontal overflow at 390px viewport width.
- Contrast pairs were pre-computed from the drafted values with a WCAG relative-luminance script during
  specification; AC-06 makes the committed test the authoritative check.

## 7. Follow-ups

These are outside this Unit and do not constrain it:

- A stronger active indicator for the sidebar item and an active style for the administrative links.
- Shell lighting and a Decisions navigation count once a global pending-decision count exists (Non-Goal 1).
