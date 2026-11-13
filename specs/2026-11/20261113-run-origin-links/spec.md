---
id: SPEC-run-origin-links
title: Run origin links and subject deep links
summary: Expose where a PR run came from (Work Item, Work Plan, SDD batch, provider session, enrollment source) on the run read, and make the run page and Attention links open their exact subject, including an SDD unit or batch on the project Repository tab.
status: planned
created: 2026-11-13
related_capabilities: []
related_usecases: []
workflow: sdd-spec-feature
---
<!-- devkit:skeleton -->

# [SPEC-run-origin-links] Run origin links and subject deep links

## 1. Problem Statement & Motivation

Handed off from proposal PROP-run-origin-links on 2026-11-13.
- **Preserved Materials**: `docs/materials/2026-11/20261113-run-origin-links`
- Target Docs Blueprint: `PROP-run-origin-links-target` (Living Spec targets for this plan and reconcile.md)

### 1. Background & Hypothesis

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
relationships without frontend derivation. Native batch links are historical-only
under `ADR-repository-owned-sdd-execution`; this proposal creates no replacement
batch control or readiness surface.

## 2. User Stories

- **US-1**: As a developer/agent, I want to implement Run origin links and subject deep links so that system capabilities are extended.

## 3. Non-Goals

1. **Scope Excluded**: <what this change will not do>

## 4. Acceptance Criteria & Behavioral Contracts

### [AC-01] <scenario>
- **Given** <precondition>
- **When** <action>
- **Then** <expected result>

## 5. Carried Proposal Notes

Sections of the proposal that did not map to a spec section. Trim or promote them while drafting; they are not contracts.

### Source feedback

- `FB-attention-sdd-batch-deep-link`: received in full. The Attention "Inspect batch" action names the batch, and the
  Repository tab opens with that batch loaded and visible; `owed-links.test.ts` and a Repository tab integration
  test cover it, and the `UX-attention` "Inspect batch" row is updated.

### 2. Planning decisions

The recommendation is evidence-derived related origins with URL-addressable Repository subjects. No schema migration
or enrollment behavior change is needed. Evidence is pinned to `e1a50a8064597d65fd44906f1b65c01ad93c2425` in
`MAT-run-origin-links-planning`.

| Question | Selected direction | Alternative and consequence |
| --- | --- | --- |
| Q1: derive or persist | Derive retained Work Item/Work Plan, Provider session and Native SDD claim/batch relationships when reading runs. Represent multiple confirmed relationships without choosing an arbitrary winner. | Persisting immutable original entry-channel metadata would require writes, migration and historical unknown values; it is unnecessary for opening retained owners. |
| Q1: enrollment source | Expose evidence categories and an explicit `unknown` when no category is proven. `unknown` never means manual, webhook or SDK. State that related origins are retained relationships, not an immutable account of the original enrollment channel. | Guessing the channel from an absent reverse link would mislabel old or independently enrolled runs. |
| Q2: read cost | Enrich the paginated run result with at most three additional bulk SELECTs: Work Item joined to Work Plan; Provider sessions; SDD claims joined to members/batches. Reuse the caller's session and transaction sequentially. | Per-run lookups grow with page size and can obscure run-list ordering/counts. Row-multiplying outer joins before pagination change the result. |
| Q3: consumers | The run page and run rows show compact related-origin links. `RunNextStep` consumes its returned Work Item/Work Plan IDs and no longer scans Work Plans; ID labels are sufficient until the destination opens. | Keeping the scan preserves unbounded browser requests and can disagree with the run read. |
| Q4: addressing | Keep `?tab=repository&unit=<encoded unit directory>`, add optional `&ref=<encoded branch>` for run links and `&batch=<UUID>`. Query parameters survive reloads and viewer switches. They are selection requests, not permission to execute. | Hash-only addressing supplies a scroll target but cannot initialize a unit or fetch a retained batch. |
| Q5: selection | A validated unit selects the SDD viewer document and descriptive activity panel together. A batch address fetches the exact project-scoped batch detail directly; it does not depend on the latest-50 list. | Loading the bounded list first can omit an older addressed batch. |

#### Read contract

The Development spec settles exact DTO names around this shape: related Work Item references include Work Plan ID;
Provider session references include catalog ID, retained session ID and its existing external session URL when
available; Native SDD references include the claim's unit and optional batch ID. Every reference is scoped to the
returned run and its project. Deduplicate identical references and order them deterministically by kind and ID.
Work Item ownership is unique in the current schema. Provider sessions and SDD claims are not unique by run, so
those references are collections. An individual SDD claim without a member has no batch. A run's existing
`sdd_snapshot.spec_dir` remains its current unit link; retained claim units are labeled as related history if a
handoff changed the current unit.

`enrollment_source` describes only what retained evidence proves: one category when exactly one category is present,
`multiple` when several categories are present, and `unknown` otherwise. Its allowed evidence categories are
`work_plan`, `provider_session` and `native_sdd`. A nonempty SDD snapshot proves a native SDD binding; it does not
prove whether the operator or Hub originally enrolled it. The interface labels this value **Related origin**.
No manual, webhook or SDK channel is inferred or promised. No immutable provenance or history surviving owner
retention is promised. A failed projection fails the read through the existing error path; an empty confirmed set
must not conceal lookup failure.

List/get, project-scoped SDD run reads and mutations returning `PipelineRunRead` use the same projection semantics.
Enrich after selecting the page; preserve `total_count`, run order and page membership. For a returned run with no
related owners, return an empty collection and `unknown`, without an extra frontend search. No database session is
opened inside serialization and no concurrent database fan-out is introduced. Development verifies the additional
statement bound on one-row and multi-row pages, alongside one checked-out connection per request. New schema fields
are additive and the generated UI client is regenerated with `just gen-ui-api`.

#### Subject links

- Work Plan and Work Item links reuse the Plans tab's existing `#work-plan-<id>` and `#work-item-<id>` addresses.
- Provider session links use the retained exact external session URL. When that URL is absent, show the retained
  session ID as text; do not pretend that a catalog-list link opens the exact session. Adding URL-addressable local
  catalog dialogs is excluded from this spec.
- Unit links use the run's project and URL-encoded current unit directory. Validate recognized proposal/spec
  directory syntax and reject traversal or arbitrary file addresses before selecting the viewer or execution panel.
  Run-generated unit URLs include `ref=<URL-encoded run.branch>` so an unmerged handoff spec opens on its recorded
  branch. Display the browse branch explicitly. A branch name is neither immutable PR-head evidence nor execution
  authority. Legacy URLs without `ref` keep the existing default-branch behavior. A missing/deleted branch shows an
  unavailable explanation and Retry/Browse escape; it never silently falls back to a different branch.
- Batch links use `/projects/<id>?tab=repository&batch=<id>`. Attention uses `context.sdd_batch_id` and the run page
  reuses the same link builder. A detail GET restores the exact batch even outside the latest-50 list. Merge the
  result into retained rows; a later **Load retained batches** action fetches the list once if not yet loaded and
  keeps the addressed selection. Repeated load clicks reuse the loaded list; explicit Refresh status remains a
  deliberate detail GET.
- If both `unit` and `batch` occur, select both independently: the document/execution region honors `unit`, and the
  read-only retained batch panel honors `batch`. No batch member is silently selected as the unit.
- A fresh address to an SDD project opens Sdd View. Switching to Git Browser preserves the address and selected unit;
  returning to Sdd View restores it. Browser back/forward or same-project query changes replace the requested
  selection. Changing project invalidates earlier requests, selection and cached list state.
- Retained batch addresses are read-only historical subjects under
  `ADR-repository-owned-sdd-execution`. Opening or changing the selected batch
  never creates/resumes native work or retransmits an old control request.
- Missing, malformed, non-SDD-project or inaccessible subjects show a visible explanation and **Browse repository**
  escape. Missing units do not enable activity start controls for that unit. A missing batch never selects another
  batch as if it were the requested one. Network errors offer Retry. Older responses cannot overwrite a later
  project or address. Opening any address sends no start/create/control mutation.

#### Acceptance examples

- **ORIGIN-01**: Given a run with a Work Item, when list/get reads return it, then the same Work Item and Work Plan IDs
  appear; a run with multiple session/claim links retains every distinct related reference without duplicating runs.
- **ORIGIN-02**: Given a direct run with no retained relationship, when it is read, then its origin is `unknown`, and
  no manual/webhook/SDK channel is invented. A projection error produces the existing failed-read response.
- **ORIGIN-03**: Given one-row and multi-row run pages, when origins are projected, then the additional SQL count is
  at most three for either page and each request uses one checked-out connection. Pagination and total are unchanged.
- **ORIGIN-04**: Given an ended Work Item run, when its page opens, then **Open Work Item recovery** targets the exact
  Work Item without a Work Plan list request. Missing/retained origin text never offers a false owner link.
- **ORIGIN-05**: Given a valid unit address, when the Repository tab opens or browser navigation changes it, then
  viewer document and execution selection agree; reload and viewer-mode switches preserve the request. An active
  run's not-yet-merged spec opens from its recorded branch; a deleted branch is explained without a false fallback.
- **ORIGIN-06**: Given an Attention item naming an old batch outside the latest 50, when **Inspect batch** opens,
  then the exact detail is fetched and visible without a batch-list prerequisite or any mutation. Later list loading
  happens once and preserves that selection.
- **ORIGIN-07**: Given an invalid/missing unit or batch, or a delayed response after an address/project change, when
  lookup settles, then the explanation/Retry/Browse escape remains accurate and no wrong subject is selected.
- **ORIGIN-08**: Given simultaneous unit and batch parameters, when the SDD view opens, then both named regions are
  selected independently and no start, batch creation or control request is sent.
- **ORIGIN-09**: Given retired batch A and batch B, when the operator changes the
  addressed selection, then the exact selected history loads without any batch
  create/resume/control request or inferred execution authority.

#### Scope and delivery

Keep one `size: L`, `task_kind: feature` spec for this read-and-link guarantee. The existing SDD-unit link gap is a
required destination integration case of the feature; it does not add another independently delivered task kind.
No migration is selected. Development remains `medium`: one Code Reviewer pass and separate cross-component
reconcile verification are required. Existing screens retain their primary actions; `target-docs.md` drafts the
changed secondary context and selection states before implementation. Optional UX review is offered by the Host.

Expected implementation paths are the declared backend feature, tests, API client, run/Attention link helpers,
Repository components and project route. New feature dependency edges are out of scope; reuse the project's existing
project-management to AI-catalog dependency. Split the origin projection/link/selection responsibilities before a
touched file exceeds the installed app-common size ceilings. Update the owning contracts and use cases listed in
`target-docs.md`; do not change current Living Spec during Planning.

Non-goals:

1. **Scope Excluded**: changing run enrollment, admission, execution, owner association, retention or recovery authority.
2. **Scope Excluded**: persisting original manual/webhook/SDK enrollment-channel history or migrating/backfilling runs.
3. **Scope Excluded**: local Provider session dialog deep links or linking a missing external session URL to another
   subject under an exact-session label.
4. **Scope Excluded**: new owed kinds, pending-decision semantics, unrelated owed links, Repository layout redesign or
   global changes to repository ref policy beyond honoring an explicitly addressed browse branch.

#### Review fold

The Challenger round identified the unmerged-unit branch gap and a missing UX register boundary; both are folded
into this recommendation. The UX review identified ambiguous pending batch-control ownership and an extension-key
collision; the drafts now name the retained request's subject and reserve `UC-execute-sdd-batch` 4d for the new
unavailable-address case. No acceptance or implementation effect is recorded by this Planning turn.

### 4. Lifecycle & Retirement Criteria

<!--
- Preliminary decisions: devkit spec proposal padr run-origin-links "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept run-origin-links --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff run-origin-links.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->

