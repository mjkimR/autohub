---
id: PROP-operator-decision-inbox-target
title: Living Spec targets for PROP-operator-decision-inbox
summary: "Candidate contract and interface updates for find pending delivery decisions across projects."
status: draft
proposal: PROP-operator-decision-inbox
created_at: 2026-11-05
targets:
  - file: docs/capabilities/delivery/CAP-PR-operator-decisions.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/usecases/delivery/UC-resolve-run-question.md
  - file: docs/usecases/sdd/UC-decide-sdd-proposal.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/delivery/UX-run-decisions.md
  - file: docs/ux/navigation/UX-app-shell.md
  - file: docs/steering/ux-objects.md
  - file: docs/architecture/ARCH-05-2-components.md
  - file: docs/ux/delivery/UX-decision-inbox.md
  - file: docs/ux/sdd/UX-sdd-workflow-request.md
  - file: docs/ux/sdd/UX-sdd-run.md
---

# [Blueprint] PROP-operator-decision-inbox: Living Spec targets

This draft records candidate reconciliation targets. It does not change the
implemented guarantees; Planning settles the final scope and screen drafts.

## 1. System Capabilities Plan

Extend `CAP-PR-operator-decisions` with ordinary pending discovery and save/application labels. Extend `CAP-SDD-native-delivery` and `CAP-SDD-workflow-control` with native discovery, exact subject identity and mandatory refreshed owner inspection. Existing mutation authority remains owned by those contracts. Reconcile `PADR-decision-inbox-read-projection` into the retained decision and its component mapping in `ARCH-05-2-components`.

## 2. Use Cases and Interface Plan

Add optional discovery entry and resolved/changed-subject extension to step 1 of `UC-resolve-run-question` and `UC-decide-sdd-proposal`, and steps 3b/3c/3d/4 of `UC-complete-sdd-workflow`. Retain their existing actor goals and mutation flows. Link those steps reciprocally to UX-decision-inbox. Extend `UX-run-decisions`, `UX-sdd-workflow-request` and `UX-sdd-run` for selected subject refresh and exact request routing. Add Decisions navigation to `UX-app-shell`.

Register pending-row representations and Review actions for existing Run question, PR run, SDD unit and Native SDD activity rows in `docs/steering/ux-objects.md`. Decision inbox is a screen, not a new domain approval object.

Draft additions to the existing object register rows (retain their other representations/actions):

| Object | Role | Representations | Calls to action |
| --- | --- | --- | --- |
| Project connection | Operator | Decision inbox project filter and row context | Filter pending decisions, open project |
| PR run | Operator | Decision inbox owner row and refreshed review dialog | Review exact decision, inspect PR |
| Run question | Operator | Ordinary pending/Answer saved row; native Hub question row using native owner behavior | Review question, save/select/dismiss through owner controls |
| SDD unit | Operator | Decision inbox proposal identity and inspected evidence head | Review proposal decision |
| Native SDD activity | Operator | Exact worker/workflow/integration row; disabled Answer publication pending row; First observed waiting label | Review exact request, inspect publication progress |


## 3. Architecture and Decision Impact

`ARCH-05-2-components` maps the pipeline-run discovery projection and native extractor to their owners. The migration is a rebuildable read model and retains no independent authority. Verify the declared lifecycle paths when implementation tasks are written.

## 4. Development Conventions and Governance

No governance or toolchain changes. Regenerate the typed UI client for the accepted API. Use existing tokens and component conventions in `src/routes/layout.css`. Inspection of tests is distinct from running them.

## 5. Before and After

Before: operators locate each project/run to discover decisions. After: one cross-project paginated screen opens an exact refreshed owner context. This is an observable navigation outcome, with no quantitative baseline or performance improvement claim.

## 6. Screens

### Candidates and recommendation

- **A — dedicated Decisions screen, recommended**: a mixed oldest-waiting worklist is primary and each Review action opens the owner dialog. This supports cross-project triage with one navigation entry.
- **B — decision grouping inside each project**: preserves current navigation but requires visiting projects and does not meet cross-project discovery without another surface.
- **C — worklist with inline action drawer**: keeps a continuous list but introduces a second composition of authority-sensitive controls and competes with the existing owner review surfaces.

Proceed with A as the within-scope Planning assumption. The Host offers this comparison for user preference and has obtained opt-in for a separate UX review.

### UX-decision-inbox — Decision inbox (screen draft)

- **Area/element**: delivery / screen.
- **Use cases**: `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`.
- **Capabilities**: `CAP-PR-operator-decisions`, `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`.

#### Purpose

- **Primary task**: Find a pending decision and open its current review context.
- **Facts to commit**: Project/run, explicit decision kind, question/request identity, saved-versus-applied state, evidence head and observation time, and waiting-age basis.
- **Secondary items**: Decision editors and complete evidence remain in `UX-run-decisions` and its native panels; history stays with the owner.

#### Content

The filtered mixed worklist is primary. Filters sit above it, and cursor navigation sits below. No approve/resume control appears in a row.

- Project connection (all-visible-projects default; optional project filter).
- Run question / Native SDD activity (kind filter and ordinary open/answered filter).
- PR run (row project, run/PR link and state).
  - Run question (title, question ID, Needs answer or Answer saved; exact waiting age).
  - Native SDD activity (request kind/title/identity, First observed waiting age, evidence head, last inspected time; Answer publication pending as a disabled review-only status while its worker envelope is being published).
  - Review (opens exact owner subject after freshness verification).
- Pagination (Next; loaded previous cursor pages; Refresh restarts at first page).
- Application shell (global navigation to other screens).

#### States

- **loading**: Explain that pending decisions are loading; filters/navigation remain accessible, Review waits for data.
- **populated**: Review any row; distinguish native observation age from ordinary waiting age. Explain that new or changed decisions can precede the current cursor and Refresh restarts the list.
- **empty**: No matching observed pending decisions; offer Clear filters and Refresh. This does not assert that every repository is live-evaluated.
- **error**: Keep filters and offer Retry; no stale row becomes actionable from the failure.
- **reviewing**: Owner dialog loads fresh context; all mutation controls disabled until exact subject validation succeeds.
- **changed**: Subject resolved, changed or unavailable; explain the outcome, refresh the worklist and offer explicit Review again for any replacement.

#### Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Review ordinary question | `UC-resolve-run-question` 1 | populated | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | Exact question and current revision load; old question cannot be substituted. |
| Review native Run question | `UC-complete-sdd-workflow` 3d | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact Hub question loads with native answer/application behavior. |
| Review proposal decision | `UC-decide-sdd-proposal` 1 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-native-delivery` | Current native evidence loads before proposal controls enable. |
| Review worker/workflow request | `UC-complete-sdd-workflow` 3b, 3c | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact request is selected in `UX-sdd-workflow-request`; missing identity requires reinspection. |
| Review integration decision | `UC-complete-sdd-workflow` 4 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | `UX-sdd-run` receives refreshed evidence and preserves approval fences. |
| Change filters | global: narrow discovery without deciding | populated | loading | | | Cursor resets; only matching visible subjects load. |
| Next / Previous | global: browse observed pending decisions | populated | loading | | | Current filters persist; unavailable cursor navigation is disabled. |
| Refresh / Retry / Clear filters | global: recover discovery | error, empty, populated | loading | | | First page reloads with selected filters or cleared filters. |
| Close owner dialog | global: return from inspection | reviewing, changed | populated | close | | Filters/page persist; focus returns to row or nearest remaining neighbor. |
| Leave Decisions | global: navigate to another task | populated, empty, error | populated | `UX-app-shell` | | Selected destination opens. |

### Review follow-up

The first separate UX review found a missing native Hub question route and undrafted register rows. Both are folded above. Its original findings remain recorded for the Host at plan-accept; Development closes them against retained screens and implementation. No prototype/browser validation is claimed.

### Owner surface amendments

`UX-run-decisions` adds selected question/request identity and a disabled loading state. After refresh, a changed subject never inherits an editor selection or typed approval from the old subject. Failed refresh offers Retry and Close. A successful save shows Answer saved and keeps the inbox entry; applying/dismissing removes it. Native controls retain all existing confirmation/reason requirements and owner errors. Closing restores the inbox state and focus. Reuse the same owner dialog reached from per-run lists.
