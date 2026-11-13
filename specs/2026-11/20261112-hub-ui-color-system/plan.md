---
id: PLAN-hub-ui-color-system
spec: SPEC-hub-ui-color-system
---

# Technical Plan: `SPEC-hub-ui-color-system` Rank operator attention in the hub-ui color system

## 1. Constitution & Invariant Review

None. No accepted ADR, `docs/architecture/` constraint or capability governs hub-ui colors; `devkit docs search`
for frontend tokens and design-system decisions returns no matching decision. The change is presentation-only inside
`modules/hub-ui` and touches no capability behavior, so `SPEC-hub-ui-color-system` lists no capability.

The color-role ranking is project-wide style background, not a contract. It goes into a new steering style file
(`docs/steering/visual-style.md`), which `ux-writing` names as the place UX documents cite for visual style. The
steering directory holds 3 of the 10 files `RULE-steering-documents` allows.

## 2. Architecture Overview & Impact

All changes are in `modules/hub-ui` plus two documentation files. No dependency is added: icons come from the
installed `@lucide/svelte`, and the contrast check implements the OKLCH-to-sRGB conversion inline.

| Area | Files | Change |
| --- | --- | --- |
| Tokens | `src/routes/layout.css` | New light/dark values; `attention` family; `@theme inline` registration |
| Primitive | `src/lib/components/ui/badge/badge.svelte` | `attention` variant |
| Document shell | `src/app.html`, `src/lib/assets/favicon.svg` | Neutral selection; ink favicon with dark-scheme stroke |
| Contrast check | `src/routes/layout-contrast.test.ts` (new) | Parses `layout.css`, asserts the AC-06 pairs |
| Run state | `pipeline-runs/presentation.ts`, `pipeline-runs/RunStateBadge.svelte` (new), `presentation.test.ts` (new) | One state → variant/icon/label mapping and component |
| Run state consumers | `PipelineRunRow.svelte`, `RunDecisionsDialog.svelte`, `repositories/SddRunLinks.svelte`, `dashboard/DashboardView.svelte` | Render `RunStateBadge` |
| Dashboard | `dashboard/DashboardView.svelte`, `dashboard/dashboard.svelte.ts`, `DashboardView.integration.test.ts` | Neutral tiles; attention Needs-you tile with breakdown and link; muted section icons |
| Inbox | `pipeline-runs/DecisionInbox.svelte`, `DecisionInbox.integration.test.ts` | Settled status labels and badges, left rule, filter option labels, outline buttons |
| Cleanup | `AppShell.svelte`, `LoginView.svelte`, `DashboardHealth.svelte`, `TaskSpecsView.svelte`, `AICatalogsView.svelte`, `NotificationsView.svelte`, `SystemConfigsView.svelte`, `ScheduleConfigsView.svelte`, `AttachPullRequestDialog.svelte`, `EnrollPullRequestDialog.svelte`, `SddRunPanel.svelte`, `JsonSchemaForm.svelte`, `AttemptHistoryDialog.svelte`, `ProjectConnectionCheckDialog.svelte`, `ProjectOverview.svelte`, `ScheduleJobsView.svelte` | Remove decorative primary; tokens for schedule job status |
| Docs | `modules/hub-ui/README.md`, `docs/steering/visual-style.md` (new) | Document `attention` and the color roles |

Paths without a prefix are under `modules/hub-ui/src/lib/features/project-management/` (pipeline-runs,
repositories) or `modules/hub-ui/src/lib/features/` (dashboard); the task boundaries give full paths.

## 3. Component & Interface Design

### 3.1 Token table (normative; OKLCH)

| Token | Light | Dark |
| --- | --- | --- |
| background | 0.985 0 0 | 0.155 0 0 |
| foreground | 0.17 0.005 260 | 0.96 0 0 |
| card, popover | 1 0 0 | 0.19 0 0 |
| card-/popover-foreground | = foreground | = foreground |
| primary | 0.24 0.012 260 | 0.93 0.005 260 |
| primary-foreground | 0.985 0 0 | 0.17 0.005 260 |
| secondary | 0.955 0 0 | 0.24 0 0 |
| secondary-foreground | 0.17 0.005 260 | 0.96 0 0 |
| muted | 0.955 0 0 | 0.22 0 0 |
| muted-foreground | 0.50 0 0 | 0.72 0 0 |
| accent | 0.94 0 0 | 0.26 0 0 |
| accent-foreground | 0.17 0.005 260 | 0.96 0 0 |
| border | 0.90 0 0 | 1 0 0 / 12% |
| input | 0.90 0 0 | 1 0 0 / 15% |
| ring | 0.45 0.01 260 | 0.75 0.005 260 |
| destructive | 0.53 0.19 27 | 0.68 0.17 25 |
| success | 0.50 0.07 160 | 0.74 0.07 160 |
| info | 0.50 0.035 250 | 0.74 0.035 250 |
| warning | 0.50 0.08 80 | 0.76 0.07 85 |
| attention | 0.78 0.165 70 | 0.82 0.16 75 |
| attention-foreground | 0.20 0.04 55 | 0.19 0.04 55 |
| attention-text | 0.50 0.13 55 | 0.82 0.16 75 |
| attention-surface | 0.97 0.04 80 | 0.24 0.05 70 |
| sidebar | 0.975 0 0 | 0.17 0 0 |
| sidebar-foreground | = foreground | = foreground |
| sidebar-primary / -foreground | = primary / primary-foreground | = primary / primary-foreground |
| sidebar-accent | 0.93 0 0 | 0.24 0 0 |
| sidebar-accent-foreground | = foreground | = foreground |
| sidebar-border | = border | = border |
| sidebar-ring | = ring | = ring |
| chart-1..5 | unchanged greyscale | unchanged greyscale |

Write each value literally (`oklch(0.24 0.012 260)`), not as `var()` aliases, so the contrast test can parse every
token. Register the four attention tokens in `@theme inline` as `--color-attention`, `--color-attention-foreground`,
`--color-attention-text` and `--color-attention-surface`.

**Token roles** (recorded in `docs/steering/visual-style.md`):

- `attention` fills an area that carries `attention-foreground` text (the Needs-you tile).
- `attention-text` is every attention mark on a neutral surface: text, icons, dots and strokes such as the inbox left
  rule. In light mode `attention` measures `2.06:1` on `card`, below the `3:1` UI threshold; `attention-text`
  measures `6.27:1`.
- `attention-surface` is the Badge background.

### 3.2 Badge `attention` variant

Add to `badgeVariants.variants.variant` in `badge.svelte`:

```ts
attention: 'border-attention-text/30 bg-attention-surface text-attention-text [a]:hover:bg-attention-surface/80',
```

Keep every other variant string unchanged (AC-03). `BadgeVariant` derives from `tv()`, so it accepts `'attention'`
without a separate type edit.

### 3.3 Run state presentation

`presentation.ts` keeps `getStateBadgeVariant` for compatibility and adds one mapping that owns variant, icon and
label:

```ts
import type { Component } from 'svelte';
export type RunStatePresentation = { variant: BadgeVariant; icon: Component; label: string };
export function getRunStatePresentation(state: RunState): RunStatePresentation;
// label = state.replaceAll('_', ' ')
// getStateBadgeVariant(state) === getRunStatePresentation(state).variant
```

The variant and icon table is AC-04. An unknown future state falls back to `secondary` with `CircleDashed`. Remove
the `warning` branch.

`RunStateBadge.svelte` (new, in `pipeline-runs/`):

```svelte
<script lang="ts">
  let { state, class: className }: { state: RunState; class?: string } = $props();
  const view = $derived(getRunStatePresentation(state));
</script>
<Badge variant={view.variant} class={cn('capitalize', className)}>
  <view.icon aria-hidden="true" /> {view.label}
</Badge>
```

Replace the four call sites with `<RunStateBadge state={...} />`. `PipelineRunRow.svelte` drops its inline
pulse/CheckCircle2/AlertCircle/PauseCircle branches and their unused imports. The label text stays lower case in the
DOM (`capitalize` is CSS), so `PipelineRunsView.integration.test.ts`'s `getByText('implementing')` keeps working.

### 3.4 Dashboard PR run summary

`dashboard.svelte.ts` adds one getter beside `failedRuns`; it reads the same `runs_by_state` and needs no API change:

```ts
get needsYouBreakdown(): string | null;
// null when stats are unavailable or failed + paused + blocked === 0
// otherwise the non-zero parts in the order failed, paused, blocked, e.g. "1 failed · 2 paused · 1 blocked"
```

In `DashboardView.svelte`, the five tiles share one neutral class string (the current Total Runs tile:
`rounded-lg border border-border/70 bg-background/50 p-3`, label `text-muted-foreground`, number in default
foreground). The Needs-you tile switches on `dashboard.failedRuns`:

| `failedRuns` | Element | Tile | Number line | Caption | Attribute |
| --- | --- | --- | --- | --- | --- |
| number > 0 | `<a href="/projects/runs">` | `border-attention bg-attention text-attention-foreground`, hover `bg-attention/90`, focus ring kept | the count | `needsYouBreakdown` | `data-attention="true"` |
| `0` | `<div>` | neutral | "No failed or held runs" | "Failed, paused, or blocked" | none |
| `'—'` | `<div>` | neutral | `—` | "Failed, paused, or blocked" | none |

The link carries no query string (AC-12): the Pipeline Runs route reads only `run` and `view`, and the list API's
`state` parameter is single-valued. Its accessible name comes from its visible text ("Needs you", the count and the
breakdown); add no `aria-label` that would hide the breakdown. Section-header icons on lines 154, 258, 273 and 328
become `text-muted-foreground`. The recent-runs badge becomes `RunStateBadge`. The polling toggle keeps
`bg-primary`.

### 3.5 Decisions inbox row

In `DecisionInbox.svelte`, derive one status per entry. These are the settled labels of AC-07:

| Condition | Badge | Content | Row |
| --- | --- | --- | --- |
| `!entry.actionable` | `info` | Clock icon + "Answer publication pending" | neutral |
| `question_state === 'answered'` | `attention` | CornerDownRight icon + "Answer saved — resume pending" | `border-l-3 border-l-attention-text`, `data-attention="true"` |
| otherwise | `attention` | `size-1.5 rounded-full bg-attention-text` dot + "Needs decision" | `border-l-3 border-l-attention-text`, `data-attention="true"` |

The label uses an em dash (U+2014) with a space on each side. Icons and the dot are `aria-hidden`. The badge
replaces the plain `<p>` text in place. The Question state filter options read "All states", "Needs decision"
(`open`) and "Answer saved — resume pending" (`answered`); their values stay. The Review, Retry and Retry review
buttons gain `variant="outline"`. Keep the article's existing border and padding. If `border-l-3` triggers
`shadcn/no-unknown-classes`, use `border-l-4`; never an arbitrary value.

### 3.6 Cleanup

- `AppShell.svelte`: delete the header `<span>` containing the pulsing dot and "Svelte 5 Runes" (lines 266-271) and
  any wrapper left empty. The sidebar logo keeps `sidebar-primary`, which becomes ink.
- Icon tiles `bg-primary/10 text-primary` → `bg-muted text-muted-foreground` in `DashboardHealth.svelte`,
  `TaskSpecsView.svelte`, `AICatalogsView.svelte`, `NotificationsView.svelte`, `SystemConfigsView.svelte`,
  `AttachPullRequestDialog.svelte`, `EnrollPullRequestDialog.svelte` and `SddRunPanel.svelte`.
- `ScheduleConfigsView.svelte` cron chip `bg-primary/10 text-primary` → `bg-muted text-muted-foreground`.
- Section-header icons `text-primary` → `text-muted-foreground` in `JsonSchemaForm.svelte`,
  `AttemptHistoryDialog.svelte` and `ProjectConnectionCheckDialog.svelte`. The Sparkles/Activity icons inside
  selected cards of `ProjectScheduleDialog.svelte` are selection indicators and stay.
- `ProjectOverview.svelte`: `hover:border-primary/50` → `hover:border-foreground/30` (three links).
- `LoginView.svelte`: delete the two `bg-primary/10 blur-3xl` backdrop divs; remove `shadow-lg shadow-primary/25`
  from the logo tile.
- `ScheduleJobsView.svelte`: `getStatusVariant` returns `{ variant: BadgeVariant; icon }` — `success`,
  `destructive`, `outline` (pending), `secondary` (other) — and the status `<span>` becomes a `Badge` with that
  variant, keeping icon and label.
- `src/app.html`: `selection:bg-primary/20 selection:text-primary` → `selection:bg-foreground/15
  selection:text-foreground`.
- `src/lib/assets/favicon.svg`: replace `stroke="#6366f1"` with an embedded style:
  `<style>svg{stroke:#1c1f25}@media (prefers-color-scheme: dark){svg{stroke:#e6e8eb}}</style>` (hex of the light
  and dark `primary`).

### 3.7 Contrast test

`src/routes/layout-contrast.test.ts` (unit project) reads `layout.css` with `node:fs`, extracts `--name: oklch(...)`
declarations from the `:root` and `.dark` blocks, converts OKLCH → linear sRGB (Björn Ottosson's matrices, clamped),
composites alpha tints in gamma-encoded sRGB over the named surface, and computes WCAG 2.x contrast. It asserts the
AC-06 pairs per theme with `test.each`, so a failure names the theme, pair and ratio. Badge tint alphas mirror
`badge.svelte`: success/info/warning `0.15`, destructive `0.10` light and `0.20` dark. Pre-computed minimums with the
section 3.1 values: light success tint over background `4.52`, dark destructive tint over card `4.52`; every other
text pair is at least `4.71`.

## 4. Error Handling & Edge Cases

- **Unknown run state**: the generated `PipelineRunState` union is closed, but the `default` branch keeps a neutral
  fallback so a newer backend value still renders a labeled badge.
- **Statistics unavailable**: `failedRuns` is `'—'`; the tile stays neutral (section 3.4), so an outage never looks
  like operator debt.
- **Native entry not actionable but unanswered**: not-actionable wins, matching the current label precedence.
- **Breakdown with stats partially missing**: a missing `runs_by_state` key counts as `0`, as `failedRuns` already
  does.
- **Size preset**: `DashboardView.svelte` has 405 lines; the tile change is net neutral. No ceiling may rise (AC-10).
  If a file approaches its limit, extract by responsibility (for example the summary tiles) rather than raising it.
- **Lint scope**: `badge.svelte` is a generated primitive excluded from `shadcn/*`; every other touched file must end
  with zero `shadcn/*` warnings.

## 5. Documentation Impact

- `docs/steering/visual-style.md` (new; frontmatter `title`, one-sentence `summary`, no `id`): color roles (ink
  actions, neutral surfaces, attention for operator debt, destructive for failures, quiet success/info/warning), the
  attention token roles of section 3.1, "never color alone: label plus icon", and "attention only on badges, tiles
  and left rules, never full row backgrounds". It cites `layout.css` as the value source and restates no values.
- `docs/steering/visual-style.md` also records that attention means operator debt, including answered-but-not-resumed
  questions and deliberately paused runs.
- `modules/hub-ui/README.md` Design-system lint: add `attention` to the status colors and Badge variants, and point
  to the steering file for when to use it.
- Reconciled at `spec-sync`, not in a task, by copying the `SPEC-hub-ui-color-system` Screens drafts:
  `UX-dashboard` (summary counts, Needs-you breakdown, "No failed or held runs" at zero, the added Interactions row
  to `UX-pipeline-runs`), `UX-decision-inbox` (the three AC-07 labels, filter option labels, "Needs answer" replaced
  by "Needs decision", the added Review saved answer row for `UC-resolve-run-question` 4) and `UX-pipeline-runs`
  (state shown as label plus icon). `UC-resolve-run-question` step 4 may add `UX-decision-inbox` to its Interface
  line. `UX-app-shell` documents no header chip, so it is unchanged.

## 6. Verification & Test Plan

| AC | Proof |
| --- | --- |
| AC-01, AC-02 | `layout-contrast.test.ts` parses every listed token (missing token fails); review of `layout.css` against section 3.1 |
| AC-03 | `just check` (type accepts `'attention'`); review of `badge.svelte` diff |
| AC-04 | `presentation.test.ts` covers all nine states (variant, icon, label) and asserts no `warning`; `rg -n "getStateBadgeVariant\(" modules/hub-ui/src` shows only `presentation.ts` and its test |
| AC-05 | `DashboardView.integration.test.ts`: count > 0 has `data-attention="true"` and the breakdown text; `0` shows "No failed or held runs" without it; failed stats show `—` without it |
| AC-12 | `DashboardView.integration.test.ts`: count > 0 renders a link with `href="/projects/runs"` whose name contains "Needs you"; at `0` there is no such link |
| AC-06 | `layout-contrast.test.ts` in `just test-ui` |
| AC-07 | `DecisionInbox.integration.test.ts`: the three exact labels; `data-attention` on the Needs decision and Answer saved — resume pending rows only; filter option texts |
| AC-08 | `rg -n "Svelte 5 Runes\|bg-primary/10\|hover:border-primary\|shadow-primary\|6366f1" modules/hub-ui/src` returns nothing outside `src/lib/components/ui/` |
| AC-09 | `rg -n "emerald\|amber" modules/hub-ui/src` returns nothing |
| AC-10 | `just lint`, `just check`, `just test-ui` exit 0; `npx --prefix modules/hub-ui eslint <touched files>` shows no `shadcn/` warning; `git diff modules/hub-ui/eslint.config.js` is empty |
| AC-11 | Existing `PipelineRunsView`, `RunDecisionsDialog`, `SddRunPanel`, `DecisionInbox` and `DashboardView` integration tests pass in `just test-ui` |

Run order per batch: `just test-ui`, then `just lint` and `just check` at the end (the backend environment must be
initialized first, per AGENTS.md). Backend tests and PostgreSQL coverage are not affected and need no rerun. A light
and dark visual pass of Dashboard, Decisions and Pipeline Runs is recommended evidence, not an acceptance gate.
