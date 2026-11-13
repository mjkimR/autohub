---
id: PROP-run-origin-links-target
title: Target Living Spec for run origin links
summary: "Draft related-origin reads and exact Repository subject selection across existing contracts, use cases and screens."
status: draft
proposal: PROP-run-origin-links
created_at: 2026-11-13
targets:
  - file: docs/capabilities/delivery/CAP-PR-pull-request-delivery.md
  - file: docs/capabilities/repository/CAP-DOC-repository-viewer.md
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/usecases/delivery/UC-deliver-pull-request.md
  - file: docs/usecases/repository/UC-inspect-repository-documents.md
  - file: docs/usecases/sdd/UC-execute-sdd-batch.md
  - file: docs/ux/delivery/UX-run-page.md
  - file: docs/ux/delivery/UX-pipeline-runs.md
  - file: docs/ux/delivery/UX-attention.md
  - file: docs/ux/repository/UX-repository.md
  - file: docs/ux/sdd/UX-sdd-batch.md
  - file: docs/steering/ux-objects.md
---

# Target Living Spec for run origin links

These are proposed Development changes. Current contracts remain unchanged during Planning.

## Document targets

| Existing document | Proposed reflection | Expected path |
| --- | --- | --- |
| `CAP-PR-pull-request-delivery` | Add evidence-derived related-origin read shape, unknown/multiple semantics, cardinality and fixed additional query bound. | `docs/capabilities/delivery/CAP-PR-pull-request-delivery.md` |
| `CAP-DOC-repository-viewer` | Add validated URL unit selection shared by document and execution panels, read-only behavior and missing-subject handling. | `docs/capabilities/repository/CAP-DOC-repository-viewer.md` |
| `CAP-SDD-native-delivery` | Document exact retained batch addressing with project-scoped GET, without create/control/admission. | `docs/capabilities/sdd/CAP-SDD-native-delivery.md` |
| `UC-deliver-pull-request` | Extend run inspection/recovery examples with exact related Work Item navigation and unknown origin. | `docs/usecases/delivery/UC-deliver-pull-request.md` |
| `UC-inspect-repository-documents` | Extend entry and selection with unit address, missing unit and stale-address responses. | `docs/usecases/repository/UC-inspect-repository-documents.md` |
| `UC-execute-sdd-batch` | Extend retained-batch inspection step 4 and reload examples with addressed old batch and missing/wrong-project outcomes. | `docs/usecases/sdd/UC-execute-sdd-batch.md` |
| `UX-run-page` | Replace frontend owner scan description, show secondary related origins and preserve the existing primary action. | `docs/ux/delivery/UX-run-page.md` |
| `UX-pipeline-runs` | Add secondary compact origin links in run rows; retain the row's primary action. | `docs/ux/delivery/UX-pipeline-runs.md` |
| `UX-attention` | Make Inspect batch open the exact `context.sdd_batch_id`; remove the deep-link follow-up statement. | `docs/ux/delivery/UX-attention.md` |
| `UX-repository` | Describe unit/batch query selection, mode persistence and unavailable subject states. | `docs/ux/repository/UX-repository.md` |
| `UX-sdd-batch` | Add addressed retained batch loading, one-time list loading, selection persistence and missing/error states. | `docs/ux/sdd/UX-sdd-batch.md` |
| UX object register | Add only the PR run, Repository viewer and SDD batch representation wording listed below. | `docs/steering/ux-objects.md` |

No new document kind or ADR is selected. The read projection and query parameters extend existing contracts without
changing an accepted architecture decision. `CAP-PR-owed-items` needs no behavior change: batch context already exists.
The source `FB-attention-sdd-batch-deep-link` is promoted to this proposal. Development verifies and reflects the
complete fix before reporting its implementation complete.

## Use case draft changes

All existing main scenarios and extensions remain. Add these entry/extension examples so the Screens can be walked:

- `UC-deliver-pull-request` step 4: while observing a run, inspect its secondary **Related origins** and follow an
  exact Work Item, SDD unit, SDD batch or retained external Provider session link. Extension *d uses returned Work
  Item/Work Plan IDs for **Open Work Item recovery**; it performs no Work Plan list scan. No related evidence displays
  **Origin unknown**, without labeling it manual or SDK. This inspection adds no execution authority.
- `UC-inspect-repository-documents` step 1 accepts a Repository URL from a run. Step 3 initializes a valid unit
  directory in both document and execution selection. Run-generated unit links carry the recorded branch in `ref`;
  legacy addresses use the default branch. The visible browse branch conveys no execution authority. Extension 3b: malformed, missing or inaccessible unit shows
  **Unit unavailable** and **Browse repository**; transient read failure adds **Retry**. Step 4 preserves the address
  through viewer switching/reload. Prior-address/project responses cannot replace current selection.
- `UC-execute-sdd-batch` step 4 accepts a Repository batch URL from Attention or a run. It reads the exact batch even
  beyond the latest-50 list and focuses its retained status region. Extension 4d: missing/wrong-project batch shows
  **Batch unavailable**, with **Browse repository**; network failure adds **Retry**. It does not select another batch
  in the requested batch's place. Batch execution controls are retired under
  `ADR-repository-owned-sdd-execution`.

## Screens

Existing layout, primary actions and unrelated state/interaction rows remain as their owning UX documents specify.
These deltas use the UX template shape; none introduces another screen or a competing primary region. The design is
an extension of existing secondary context, so no alternative page arrangement is open.

### `UX-run-page` delta

- **Element**: screen.
- **Use cases**: `UC-deliver-pull-request`, `UC-resolve-run-question`, `UC-decide-sdd-proposal`, `UC-complete-sdd-workflow`.
- **Purpose**: Take the run's next required action. State, PR identity, wait reason and decision are the facts for
  that action. Related origin inspection remains secondary below the header/action row and before history.
- **Content**: PR run header/actions remain primary; **Related origins** presents Work Plan/Work Item IDs, current
  SDD unit path, related claim unit paths, SDD batch IDs and available exact external Provider session links as compact
  labeled links. Related history is labeled separately from the current unit. An unavailable external session URL
  leaves a session ID as text. **Origin unknown** explains that no retained origin proves an entry category.
  Ended Work Item runs reuse **Open Work Item recovery** with the returned IDs; no owner title fetch is required.
- **States**: existing loading/populated/ended/error/not-found/operating states remain. Missing origin evidence is
  populated data, not an error. Failed run read keeps the existing Retry path; a failed refreshed read keeps previous
  consistent data. An unavailable related subject is explained by its destination. No origin action approves work.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Open Work Item recovery | `UC-deliver-pull-request` *d | ended | populated | `UX-work-plans` | Exact Work Item is expanded from the returned ID, without a Work Plan list scan. |
| Open current/related SDD unit or batch | `UC-deliver-pull-request` 4 | populated, ended | populated | `UX-repository` | The named unit/batch is selected or its explicit unavailable state appears. |
| Open Provider session | global: inspect retained external execution evidence | populated, ended | populated | end | Existing exact provider URL opens separately; missing URL is text without a false link. |
| Open Work Plan or Work Item | `UC-deliver-pull-request` 4 | populated, ended | populated | `UX-work-plans` | The existing Plans anchor opens the exact object. |
| Back to project runs | global: leave run inspection | populated, ended, error, not-found | populated | `UX-pipeline-runs` | Return to the existing run list. |

### `UX-pipeline-runs` delta

- **Element**: screen.
- **Use cases**: `UC-deliver-pull-request` (existing unrelated use cases and controls remain).
- **Purpose**: Find a run and its required action. Project, PR identity, state and wait reason remain the primary
  row context. Related origin links are secondary text in the same row, without a new primary action or filter.
- **Content**: each PR run row adds the same compact known related references as the run page. Multiple relationships
  remain distinguishable. **Origin unknown** never asserts manual enrollment. Provider URLs absent from evidence
  remain text. Long identifiers wrap within the existing row's secondary region.
- **States**: existing populated/loading/empty/error states remain. Origin projection belongs to the run read; no
  per-row browser loading request is added. Failed refresh retains the existing error/Retry path.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Open related unit/batch | `UC-deliver-pull-request` 4 | populated | populated | `UX-repository` | Exact named subject or unavailable explanation opens. |
| Open related Work Plan/Work Item | `UC-deliver-pull-request` 4 | populated | populated | `UX-work-plans` | Exact existing Plans anchor opens. |
| Open run | `UC-deliver-pull-request` 4 | populated | populated | `UX-run-page` | Run context and its existing primary action open. |
| Open Provider session | global: inspect external source evidence | populated | populated | end | Known exact provider URL opens separately. |

### `UX-repository` delta

- **Element**: panel.
- **Use cases**: `UC-inspect-repository-documents`, `UC-execute-sdd-batch`.
- **Purpose**: Inspect repository documents at the selected branch and open retained execution context. Repository
  identity/ref/path remain the facts for inspection. Batch status remains the existing linked panel above the viewer.
- **Content**: branch/mode controls remain above the content. A valid `unit` directory initializes both SDD document
  and descriptive activity selection. A `batch` ID is passed to `UX-sdd-batch`; it does not change the selected unit. Both may
  coexist. An explicit `ref` initializes the visible browse branch, including an active run's unmerged handoff spec.
  Missing branches do not silently fall back. Without `ref`, use the existing default branch. Initial SDD addresses
  open Sdd View; later mode switches preserve query and selection. The browse branch is not immutable PR-head
  evidence and conveys no execution authority.
- **States**: populated/loading/empty/error remain. **unit-unavailable** names the requested unit and explains
  malformed/missing/non-SDD/inaccessible selection or a missing addressed branch; **Browse repository** clears the unit request and resets an unavailable addressed ref to the default branch before
  ordinary browsing. Transient failure offers **Retry**. Unknown units enable no native activity-start controls.
  **batch-unavailable** is confined to `UX-sdd-batch`; valid unit inspection remains available. Query/project changes
  invalidate earlier lookups. A non-SDD project explains unsupported SDD selection without hiding Git Browser.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Open or navigate to unit address | `UC-inspect-repository-documents` 1, 3 | populated, loading | populated, unit-unavailable, error |  | Document and execution panel agree on the validated unit or explain unavailability. |
| Open or navigate to batch address | `UC-execute-sdd-batch` 1 | populated | loading | `UX-sdd-batch` | Exact retained batch lookup begins without mutations or a latest-list prerequisite. |
| Sdd View / Git Browser | global: select repository representation | populated | populated |  | Address is kept; returning to Sdd View restores the selection. |
| Retry unit | `UC-inspect-repository-documents` 3b | error | loading |  | Repeat only the current selection's failed read. |
| Browse repository | `UC-inspect-repository-documents` 3b | unit-unavailable, error | populated |  | Remove the unit request and return to normal repository browsing. |
| Leave Repository tab | global: return to project task context | populated, unit-unavailable, error | populated | `UX-project-detail` | Existing project navigation remains available. |

### `UX-sdd-batch` delta

- **Element**: panel.
- **Use cases**: `UC-execute-sdd-batch`.
- **Purpose**: Inspect an exact retained batch's historical status. Batch ID,
  revision, state and stored outcomes stay primary; no live create/admission controls remain.
- **Content**: addressed batch heading shows its ID, state/revision and retained members/claims. The detail result is
  merged into retained options even when older than the latest list. After load, focus/scroll the heading with the
  stable `sdd-batch-<id>` element ID. A detail GET does not load/reconcile/admit anything beyond observation.
  **Load retained batches** loads the bounded options once per project/mount; it keeps the addressed selection.
  **Refresh status** deliberately reloads only the selected batch. Opening both unit and batch keeps both regions.
- **States**: existing durable states remain. **loading** announces the exact requested ID. **batch-unavailable**
  names the absent/malformed/wrong-project ID and offers **Browse repository**; no other batch is substituted.
  **error** keeps the requested ID and offers **Retry**. Historical control
  receipts remain inspect-only, and navigation never retransmits them. The exact
  selected subject stays separate from earlier retained outcomes. Older
  project/address responses cannot overwrite current data.

| Trigger | Step | From | To | Target | Feedback |
| --- | --- | --- | --- | --- | --- |
| Open exact batch address / Retry | `UC-execute-sdd-batch` 1 | populated, error | loading |  | Exact detail GET selects the named batch or explains failure; sends no mutation. |
| Load retained batches | `UC-execute-sdd-batch` 1 | populated | populated, error |  | First list GET adds options and preserves selection; repeated clicks do not refetch. |
| Refresh status | `UC-execute-sdd-batch` 1 | populated | loading |  | Explicit selected detail GET refreshes the retained revision. |
| Browse repository | `UC-execute-sdd-batch` 1a | batch-unavailable, error | populated | `UX-repository` | Clear the batch query and continue document browsing. |
| Return to repository | `UC-execute-sdd-batch` 3 | populated | populated | `UX-repository` | Batch remains retained; leaving the panel does not control it. |

## Draft UX object register additions

Existing objects and calls to action in `docs/steering/ux-objects.md` cover these inspections. Add **related-origin
links** to PR run representations, **addressed unit selection** to Repository viewer representations and **addressed
retained batch** to SDD batch representations. Calls to action remain inspect/open/browse/refresh; no new approval or
execution action is introduced. Reflect these wording additions only if the register's body limit permits; otherwise
name their omission in the Development UX verification and keep the element details in their owners.

## Verification targets

Development adds backend projection/cardinality/unknown/pagination/query-budget checks on SQLite and PostgreSQL;
UI link-builder and run-page integration checks; Repository route integration checks for direct/reloaded/navigation
addresses, an unmerged spec on its run branch, deleted branches, missing subjects, old batches outside latest 50,
one-time list loading, retained outcome A while inspecting B and stale response races. These are
planned checks, not executed results. Use existing integration tests and split authored components to meet the
installed app-common structure limits. Run `just gen-ui-api`, `just lint`, `just check` and relevant tests before
Development completion.
