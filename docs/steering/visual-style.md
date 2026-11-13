---
title: Visual style
summary: "Read before choosing a color, Badge variant or emphasis for a hub-ui screen or UX document; defines which color role marks actions, surfaces, operator debt, failures and routine status."
---

# Visual style

Saturated color in hub-ui marks operator debt: work that waits for the operator, and failures. Everything else is ink
or neutral grey, so an exception is the most salient element on a screen. Token values live in
`modules/hub-ui/src/routes/layout.css`; this file names the roles and does not restate values.

## Color roles

| Role | Tokens | Use for |
| --- | --- | --- |
| Ink | `primary`, `foreground`, `ring` | Actions, controls, selected and active states, the logo and favicon |
| Neutral | `background`, `card`, `popover`, `muted`, `secondary`, `accent`, `border`, `sidebar*` | Surfaces, icon tiles, decorative and section-header icons, hover borders |
| Attention | `attention`, `attention-foreground`, `attention-text`, `attention-surface` | Work waiting for the operator |
| Failure | `destructive` | Failed work and destructive actions |
| Quiet status | `success`, `info`, `warning` | Routine progress, completion and non-blocking caveats |

- Use ink for every action and control. A routine control, such as Resume or Pause on a run row, carries no status
  hue, because a hued control competes with the status it acts on.
- Form controls take ink too: focus uses `ring`, and checked checkboxes and radios use `primary`. `layout.css`
  overrides the blue defaults of `@tailwindcss/forms`.
- Use neutral surfaces for decoration. An icon tile is `bg-muted` with `text-muted-foreground`, never a tinted
  `primary`.
- Use the `destructive` Badge or Button variant for a failed run, a failed job or a destructive action. Do not use it
  for work that is held for the operator.
- Use `success`, `info` and `warning` for routine signals. Their chroma stays low so they never outrank attention or
  failure.
- Do not give a live or routine indicator or loading text motion, such as `animate-pulse`. Show liveness with an
  icon and text, and loading with static `role="status"` text. A spinning icon is reserved for the control whose
  action is in flight, such as a busy Refresh button.
- Use theme tokens and component variants, not the raw Tailwind palette (`modules/hub-ui/README.md`, Design-system
  lint).

## Attention

Attention means operator debt: a paused or blocked PR run, a Run question awaiting a decision, and an answered Run
question whose run has not resumed. A deliberately paused run is attention too, because only the operator can resume
it.

- Show attention only on a Badge, a summary tile, a row's left rule or the application shell's top rule (2px, while
  pending decisions are owed; `UX-app-shell`). Never fill a full row background with it, because dense amber lists
  cause alarm fatigue and lower text contrast.
- Keep the left rule for attention. Selected and active states, such as the active sidebar link, use ink: a 1px
  `sidebar-ring` outline with semibold text, never a hued or left-edge mark.
- Use the `attention` fill only on an area whose text is `attention-foreground`, such as the dashboard Needs-you
  tile.
- Use `attention-text` for every attention mark on a neutral surface: text, icons, dots and strokes such as the
  Decisions inbox left rule and the shell top rule. The `attention` fill is too light to meet the 3:1 UI threshold as
  a stroke on a light card.
- Use the `attention` Badge variant for a labeled status; it pairs `attention-surface` with `attention-text`.
- Show attention only when the count or condition is present. A zero or unknown count stays neutral, so an outage
  never looks like operator debt.

## Status is never color only

- Every status shows a text label and an `aria-hidden` icon or dot beside it, so it reads in monochrome, with a
  screen reader and in both themes.
- Give each state of one status family a distinct icon. The PR run state badge maps each state to one variant, icon
  and label in `modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.ts`.
- Write every label in display case in code, not with CSS `capitalize`, so acronyms such as CI, PR, SDD and AI keep
  their case. Map raw state or status values to labels with `displayLabel` (`modules/hub-ui/src/lib/labels.ts`)
  and a written label map, kept beside the presentation mapping when several surfaces show the same values.

## Contrast

- Text pairs meet at least 4.5:1, including status text on its Badge tint over the card and over the background.
- UI component pairs meet at least 3:1: the focus ring, the ink primary and every attention stroke or dot against
  the surface it sits on.
- `modules/hub-ui/src/routes/layout-contrast.test.ts` parses `layout.css`, composites Badge tints over their surface
  and fails `just test-ui` when a key pair in either theme falls below its threshold. Add a pair to that test when a
  new token pair carries text or a required UI mark.
