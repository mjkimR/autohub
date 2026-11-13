---
reconcile_id: REC-hub-ui-color-system
status: resolved
targets:
  - file: docs/ux/operations/UX-dashboard.md
    resolution: modified
  - file: docs/ux/delivery/UX-decision-inbox.md
    resolution: modified
  - file: docs/ux/delivery/UX-pipeline-runs.md
    resolution: modified
  - file: docs/usecases/delivery/UC-resolve-run-question.md
    resolution: modified
  - file: docs/steering/visual-style.md
    resolution: modified
  - file: docs/README.md
    resolution: modified
---

# Reconcile: `SPEC-hub-ui-color-system`

## Reflected changes

- `UX-dashboard`: PR run summary counts are four neutral tiles plus the Needs-you tile (failed, paused or blocked),
  which alone carries attention emphasis above zero, shows the per-state breakdown caption and links to
  `UX-pipeline-runs`; at zero it reads "No failed or held runs" and at unknown it shows the unknown marker, both
  neutral and unlinked (AC-05, AC-12). The recent list uses the PR run state badge (AC-04), the live-refresh
  indicator has no motion, and the Needs-you navigation row is added to Interactions.
- `UX-decision-inbox`: the three AC-07 decision status labels with their emphasis, icon and left-rule conditions,
  the Question state filter labels ("Needs answer" is now "Needs decision"), outline Review/Retry/Retry review, no
  attention marks in loading, empty and error, and the added Review saved answer row for
  `UC-resolve-run-question` 4.
- `UX-pipeline-runs`: the row state is the PR run state badge ranked by role (AC-04), the pause reason stays below it,
  Pause/Resume are ink, operating keeps the badge until the refreshed state arrives, and the screen is the target of
  the dashboard Needs-you tile.
- `UC-resolve-run-question`: step 4 names `UX-decision-inbox` in its Interface line, reciprocal to the new
  Interactions row.
- `docs/steering/visual-style.md`: created in T5 on this branch (color roles, attention as operator debt, never color
  alone); the UX documents cite it instead of restating tokens. Its display-case and no-motion rules apply to new or
  changed labels and indicators and to casing-sensitive labels; existing remnants are deferred work.
- `docs/README.md`: the Read by purpose table lists the visual style steering file.

## No impact

- Capabilities: no behavior, API or business rule changed (Non-Goal 2); `CAP-PR-operator-decisions` and
  `CAP-PR-pull-request-delivery` describe no colors or labels touched here.
- `UX-app-shell`: it never documented the removed "Svelte 5 Runes" chip or the "Scheduler Manager" subtitle, so it is
  unchanged.
- `UX-run-decisions`, `UX-sdd-execution` and `UX-schedule-jobs`: their labels, icons and variants did change (the
  shared run state badge in the run decisions header and SDD run links; Badge variants for Schedule job statuses),
  but these documents name the run state or job status badge without setting its label, icon or emphasis. The
  shared run state badge (`presentation.ts`, the PR run "state/lease context" representation in
  `docs/steering/ux-objects.md`) and `docs/steering/visual-style.md` own those details, so the documents stay
  accurate unchanged.
- `docs/steering/ux-objects.md`: the PR run row already names its state representation; the register is unchanged.
- Glossary: no domain term was introduced or renamed; `attention` is a visual role owned by
  `docs/steering/visual-style.md`.
- Architecture and decisions: no structural change and no ADR-level decision; the token choices live in the plan
  and `docs/steering/visual-style.md`.
- `modules/hub-ui/README.md` (Design-system lint and the "Autohub" opening) is a contributor guide changed in T5,
  not a Living Spec target.

## Deferred work

- `FB-sidebar-active-indicator`: stronger sidebar active indicator and an administrative-link active style
  (section 7 Follow-ups).
- `FB-hub-ui-capitalize-pulse-remnants`: untouched hub-ui labels still using CSS `capitalize` and loading text
  still using `animate-pulse` (reconcile-check-01 finding 3).
- `FB-shell-pending-decision-count`: shell lighting and a Decisions navigation count once a global pending-decision
  count source exists (Non-Goal 1, section 7 Follow-ups).

## Authority

Contract amendments made during build-verify (display-case run labels, the 390px overflow fix, the subtitle removal
and README "Autohub" opening) are approved by `user`, recorded in `SPEC-hub-ui-color-system` section 6.
