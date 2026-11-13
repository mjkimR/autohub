---
id: PROP-run-origin-links
title: Run origin links and subject deep links
summary: "Expose where a PR run came from (Work Item, Work Plan, SDD batch, provider session, enrollment source) on the run read, and make the run page and Attention links open their exact subject, including an SDD unit or batch on the project Repository tab."
status: reviewing                     # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: capabilities/delivery/
priority: medium                      # critical | high | medium | low
size: L                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: medium               # low | medium | high (hint for Planning)
dev_effort: medium                    # low | medium | high (hint for Development)
boundaries:
  owns:
    - capabilities/delivery/
    - ux/delivery/
    - ux/repository/
    - ux/sdd/
    - modules/hub/app/features/project_management/
    - modules/hub/tests/
    - modules/hub-ui/src/lib/api/
    - modules/hub-ui/src/lib/features/attention/
    - modules/hub-ui/src/lib/features/project-management/pipeline-runs/
    - modules/hub-ui/src/lib/features/project-management/repositories/
    - modules/hub-ui/src/lib/features/project-management/projects/
    - modules/hub-ui/src/routes/projects/
  excludes:
    - docs/decisions/
    - modules/hub-ui/src/lib/features/project-management/work-plans/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-run-origin-links] Run origin links and subject deep links

## 1. Background & Hypothesis

Split off from the original proposal of `SPEC-owed-item-contract` on the user's decision in its Planning: run origin
fields serve the run page, not the owed-item contract, whose subject needs only type, ID and project.

The app-wide UX review of 2026-11-13 (designer increment I5; relationships R4, R11 and R19) found that a PR run has no
path back to where it came from. `PipelineRun` and `PipelineRunRead`
(`modules/hub/app/features/project_management/pipeline_runs/schemas.py`) carry no Work Item, Work Plan, SDD batch,
provider session or enrollment source. Links exist only on the other side: `WorkItem.pipeline_run_id`,
`AICatalogSession.pipeline_run_id` and `SddActivityClaim.run_id`. No enrollment source is persisted. Evidence:
`docs/materials/2026-11/20261113-owed-item-contract/owed-state-inventory.md`.

The missing back-link already costs the run page a derivation: `RunNextStep.svelte`
(`modules/hub-ui/src/lib/features/project-management/pipeline-runs/run-page/RunNextStep.svelte`) pages through every
Work Plan of the project to find the Work Item whose `pipeline_run_id` names the run, because "the run carries no
Work Item reference".

The same review left two subject deep links unfinished on the hub-ui side, both landing on the project Repository tab
without selecting what they name:

- **SDD unit link from the run page**: `RunPageView.svelte` links an SDD run to
  `/projects/<id>?tab=repository&unit=<spec_dir>`, and `UX-run-page` states that the link "opens the project
  Repository tab with that unit". No code reads `unit`: the route
  (`modules/hub-ui/src/routes/projects/[projectId]/+page.svelte`) passes only `tab` to `ProjectDetailView`, which
  renders `<RepositoryView {project} />`; `RepositoryView.svelte` reads no URL parameter, resets `selectedSpec` to
  empty on every project change and sets it only from the `SddViewer` `onselectpath` callback, and opens the viewer at
  the fixed `initialPath="docs/"`. `RunPageView.integration.test.ts` asserts the URL string only, so the gap is
  untested. The `UX-run-page` Interactions row already describes the real behavior ("The project's Repository tab
  opens"), so the document contradicts itself.
- **SDD batch link from Attention** (`FB-attention-sdd-batch-deep-link`): `owedHref` in
  `modules/hub-ui/src/lib/features/attention/owed-links.ts` maps `sdd-batch-attention` to
  `projectTabHref(project, 'repository')` and ignores `context.sdd_batch_id`, which `CAP-PR-owed-items` already
  returns. `SddBatch.svelte` (inside `SddMilestonePreview.svelte`) shows batches only after the operator presses
  "Load retained batches" and picks one from a select; it has no element ID per batch. `UX-attention` records the
  batch deep link as a follow-up in its "Inspect batch" row. Work Plans and Work Items already have the pattern to
  follow: `WorkPlansPanel.svelte` scrolls to `#work-plan-<id>` and `#work-item-<id>`.

Hypothesis: exposing origin links on the run read, and giving the Repository tab URL-addressable unit and batch
selection, lets every run page link, run row and Attention action open its exact subject, closing the one-way
relationships without frontend derivation.

## Source feedback

- `FB-attention-sdd-batch-deep-link`: received in full. The Attention "Inspect batch" action names the batch, and the
  Repository tab opens with that batch loaded and visible; `owed-links.test.ts` and a Repository tab integration
  test cover it, and the `UX-attention` "Inspect batch" row is updated.

## 2. Technical Spike Questions

- **Q1 (derive or persist)**: Are origin links derived at read time from the existing reverse links, or persisted on
  the run? Is an enrollment source (manual enrollment, Work Plan, native SDD, SDK) recoverable for existing runs?
- **Q2 (read cost)**: How do origin joins stay within the shared connection budget on run list pages?
- **Q3 (consumers)**: Which UI surfaces land with the fields (`UX-run-page`, run rows), and which follow? Does
  `RunNextStep.svelte` switch from paging Work Plans to the run's own Work Item reference in this work?
- **Q4 (Repository tab addressing)**: What is the URL contract for a unit and a batch on the Repository tab: the
  existing `unit` query parameter plus a `batch` parameter, or hash anchors such as `#sdd-batch-<id>` like the Plans
  tab? Which one survives the tab's viewer-mode switch and a reload, and what shows when the named unit or batch no
  longer exists?
- **Q5 (selection reach)**: Does a selected unit drive `SddViewer` (`initialPath`) and `SddExecution`
  (`selectedSpec`) together, and does a batch link load retained batches once (one
  `GET /api/v1/projects/{project_id}/sdd/batches` read, then the batch read) without a second load on the operator's
  later "Load retained batches"?

## 3. Proposed Design & Impact

Direction, to be settled in Planning:

1. **Run read**: add origin fields to the run read (Work Item and Work Plan IDs, SDD batch ID, provider session ID,
   enrollment source), with deep-link-ready IDs and the project.
2. **Run page and run rows**: link each origin to its owner screen; the Work Item link replaces the Work Plan scan in
   `RunNextStep.svelte` when Q3 says so.
3. **Repository tab addressing**: `RepositoryView` honors a unit address (the existing `?tab=repository&unit=` link
   from `RunPageView.svelte`) by selecting that unit in the SDD viewer and execution panel, and a batch address by
   loading the retained batches and showing the named batch.
4. **Attention mapping**: `owedHref` maps `sdd-batch-attention` with `context.sdd_batch_id` to the batch address;
   run origins that name an SDD batch reuse the same address.

Expected impact: the delivery capability's run read contract, `UX-run-page`, `UX-attention`, `UX-repository`,
`UX-sdd-batch`, typed client regeneration (`just gen-ui-api`), and possibly a migration if Q1 persists an enrollment
source. `CAP-PR-owed-items` keeps its contract: `context.sdd_batch_id` already exists.

Size: `L`, not `XL`. The fold adds hub-ui consumers and one Repository tab addressing change to the original
backend-plus-run-page scope; all parts serve one guarantee (a link names and opens its subject), share the batch
address and land in one feature spec with one `task_kind`. If Q1 settles on a persisted enrollment source with a
backfill migration, Planning should re-check whether the frontend deep links still fit the same spec.

Non-goals:

1. The per-run pending-decision flag, which `SPEC-owed-item-contract` delivers.
2. Changing how runs are enrolled or linked.
3. Deep links for owed kinds that already open their subject (decisions, runs, Work Plans, Work Items) and the
   connection-test cleanup link to the Connections tab.
4. Redesigning the Repository tab, the SDD viewer or the batch panel beyond selecting the addressed unit or batch.

## 4. Lifecycle & Retirement Criteria
<!--
- Preliminary decisions: devkit spec proposal padr run-origin-links "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept run-origin-links --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff run-origin-links.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->
