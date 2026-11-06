---
id: UX-decision-inbox
title: Decision inbox
summary: "Discover observed pending decisions across projects and open the exact owner review with current native evidence."
area: delivery
element: screen
status: active
usecases:
  - UC-receive-decision-notice
  - UC-resolve-run-question
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
capabilities:
  - CAP-PR-operator-decisions
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
---

# [UX-decision-inbox] Decision inbox

## 1. Purpose

- **Primary task**: Find a pending decision and open its current review context.
- **Facts to commit**: Project/run, explicit decision kind, question/request identity, saved-versus-applied state, evidence head and observation time, and waiting-age basis.
- **Secondary items**: Decision editors and complete evidence remain in `UX-run-decisions` and its native panels; history stays with the owner.

## 2. Content

The filtered mixed worklist is primary. Filters sit above it, and cursor navigation sits below. No approve/resume control appears in a row.

- Project connection (all-visible-projects default; optional project filter).
- Run question / Native SDD activity (kind filter and ordinary open/answered filter).
- PR run (row project, run/PR link and state).
  - Run question (title, question ID, Needs answer or Answer saved; exact waiting age).
  - Native SDD activity (request kind/title/identity, First observed waiting age, evidence head, last inspected time; Answer publication pending as a disabled review-only status while its worker envelope is being published).
  - Review (opens exact owner subject after freshness verification).
- Pagination (Next; loaded previous cursor pages; Refresh restarts at first page).
- Application shell (global navigation to other screens).

## 3. States

- **loading**: Explain that pending decisions are loading; filters/navigation remain accessible, Review waits for data.
- **populated**: Review any row; distinguish native observation age from ordinary waiting age. Explain that new or changed decisions can precede the current cursor and Refresh restarts the list.
- **empty**: No matching observed pending decisions; offer Clear filters and Refresh. This does not assert that every repository is live-evaluated.
- **error**: Keep filters and offer Retry; no stale row becomes actionable from the failure.
- **reviewing**: Owner dialog loads fresh context; all mutation controls disabled until exact subject validation succeeds.
- **changed**: Subject resolved, changed or unavailable; explain the outcome, refresh the worklist and offer explicit Review again for any replacement.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Review ordinary question | `UC-resolve-run-question` 1 | populated | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | Exact question and current revision load; old question cannot be substituted. |
| Review native Run question | `UC-complete-sdd-workflow` 3d | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact Hub question loads with native answer/application behavior. |
| Review proposal decision | `UC-decide-sdd-proposal` 1 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-native-delivery` | Current native evidence loads before proposal controls enable. |
| Review worker/workflow request | `UC-complete-sdd-workflow` 3b, `UC-complete-sdd-workflow` 3c | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | Exact request is selected in `UX-sdd-workflow-request`; missing identity requires reinspection. |
| Review integration decision | `UC-complete-sdd-workflow` 4 | populated | reviewing | `UX-run-decisions` | `CAP-SDD-workflow-control` | `UX-sdd-run` receives refreshed evidence and preserves approval fences. |
| Change filters | global: narrow discovery without deciding | populated | loading | | | Cursor resets; only matching visible subjects load. |
| Next / Previous | global: browse observed pending decisions | populated | loading | | | Current filters persist; unavailable cursor navigation is disabled. |
| Refresh / Retry / Clear filters | global: recover discovery | error, empty, populated | loading | | | First page reloads with selected filters or cleared filters. |
| Close owner dialog | global: return from inspection | reviewing, changed | populated | close | | Filters/page persist; focus returns to row or nearest remaining neighbor. |
| Leave Decisions | global: navigate to another task | populated, empty, error | populated | `UX-app-shell` | | Selected destination opens. |
| Follow authenticated notice link | `UC-receive-decision-notice` 1, `UC-receive-decision-notice` 2 | populated | link-reviewing | | `CAP-PR-operator-decisions` | Exact review identity loads even outside the first page. |
| Exact owner review succeeds | `UC-receive-decision-notice` 3 | link-reviewing | reviewing | `UX-run-decisions` | `CAP-PR-operator-decisions` | Only the selected question/request opens with existing native panels as appropriate. |
| Retry review | `UC-receive-decision-notice` 2b | link-error | link-reviewing | | `CAP-PR-operator-decisions` | Repeats exact authenticated inspection, not a decision mutation. |
| Open/Refresh inbox | `UC-receive-decision-notice` 1a, `UC-receive-decision-notice` 2a | link-invalid, link-changed, link-error | loading | | | Clears obsolete selection and shows current discovery without automatically opening a replacement. |
| Close owner review / leave Decisions | global: return from exact inspection | reviewing, populated | populated | close | | Keeps ordinary list context and restores focus to landing action when no originating row exists. |

## 5. Evidence

Source: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.svelte`.
Interaction assertions: `DecisionInbox.integration.test.ts` covers filters, cursor pages and focus restoration. This source-derived contract claims no live repository walkthrough or deployment.

## 6. Exact notice landing

### Content

Keep the current filtered worklist primary. An exact link adds a visible landing-status region while authenticated owner review runs, independent of list pagination/filter state. Show key/kind provenance and observed basis without question text before owner authorization. Password sign-in retains the original encoded query in place. Google sign-in uses the bounded exact-key/fingerprint return helper specified above, without an arbitrary redirect target. Lookup returns the exact server-bound Entry before existing owner review returns its Run; no paginated list scan or inferred subject is allowed. After exact success, the existing owner dialog is the primary decision surface. The link does not save answers, grant approval or resume work.

### States

Keep existing states; add **link-reviewing** with inspection status and Open inbox; **link-changed** for missing/replaced/inaccessible evidence with Refresh inbox; **link-error** with Retry review/Open inbox; **link-invalid** with no request and Open inbox. Automatic initial link review runs once per exact URL identity; rerendering or owner-dialog dismissal does not loop inspection. Failed/dismissed inspection requires explicit Retry review. Ordinary/native head/generation changes never select another subject automatically.

### Interactions
