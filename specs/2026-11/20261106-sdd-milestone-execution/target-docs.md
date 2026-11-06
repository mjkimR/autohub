---
id: PROP-sdd-milestone-execution-target
title: Living Spec targets for PROP-sdd-milestone-execution
summary: "Candidate contract and interface updates for execute selected sdd milestone work sequentially."
status: draft
proposal: SPEC-sdd-milestone-execution
created_at: 2026-11-05
targets:
  - file: docs/capabilities/sdd/CAP-SDD-native-delivery.md
  - file: docs/capabilities/sdd/CAP-SDD-workflow-control.md
  - file: docs/capabilities/execution/CAP-EXEC-scheduling-maintenance.md
  - file: docs/usecases/sdd/UC-start-sdd-activity.md
  - file: docs/usecases/sdd/UC-complete-sdd-workflow.md
  - file: docs/ux/sdd/UX-sdd-execution.md
  - file: docs/usecases/sdd/UC-execute-sdd-batch.md
  - file: docs/ux/sdd/UX-sdd-batch.md
  - file: docs/capabilities/sdd/CAP-SDD-runtime-isolation.md
  - file: docs/steering/glossary.md
  - file: docs/steering/ux-objects.md
  - file: docs/architecture/ARCH-06-execution.md
---

# [Blueprint] PROP-sdd-milestone-execution: Living Spec targets

## 1. System Capabilities Plan

Extend `CAP-SDD-native-delivery` with explicit execution selection, immutable ledger, single-batch/member exclusion, fresh dependency/admission checks, canonical lineage, control receipts and recovery boundaries. Replace its milestone-batch exclusion only for this bounded sequential path. Preserve individual admission parity and existing decision/PR ownership in `CAP-SDD-workflow-control`. Describe fresh per-activity evaluation and retained admitted identity in `CAP-SDD-runtime-isolation`, without weakening isolation or drift refusal. Extend `CAP-EXEC-scheduling-maintenance` with bounded fair batch reconciliation and unresolved-run retention.

The accepted design carried into `SPEC-sdd-milestone-readiness` remains provisional until its implementation lands. Its eligible-only ephemeral subset remains observation-only. This feature adds a distinct execution selection that can include supported dependency-held direct proposals as explicitly waiting future intent. Name this same-feature prerequisite impact at plan-accept and compare it against the landed predecessor before Development/handoff.

## 2. Use Cases and Interface Plan

Create UC-execute-sdd-batch with these steps, all citing UX-sdd-batch unless another interface is named:

1. Enter from the milestone preview with its project/ref/milestone and complete captured SHA. The operator explicitly chooses execution selection, initially empty.
2. Select supported direct members, including explicitly waiting prerequisite-held members. Inspect exact IDs/order, current versus future eligibility, outside prerequisites, both activity phases, effort/catalog preferences and current holds.
3. Confirm the immutable selection and through-Development intent. Hub rechecks the pinned basis and creates a durable batch receipt. This confirms execution intent only; the panel states existing gates remain separate.
4. Follow one admitted activity and its current phase, exact base/lineage, owner result and next prerequisite hold. Open the existing run for plan-accept, handoff, questions and integration decisions through `UX-sdd-run`, `UX-sdd-workflow-request` and `UX-run-decisions`.
5. Pause/resume future admission or confirm Stop future admission. Inspect the returned revision and any already-admitted in-flight activity.
6. Inspect completed, stopped or attention outcomes and return to repository/preview content.

Extensions:

- **2a**: Incomplete/unknown/unsupported discovery disables execution selection; refresh or inspect exact source errors.
- **3a**: SHA, project or membership changed: creation conflicts, clears stale selection and offers a fresh preview; no admission occurs.
- **3b**: Response lost: retain request identity in UI until receipt lookup/replay resolves it. Never generate a second create request automatically.
- **4a**: Exact dependencies remain unfinished or handed-off PROP needs canonical repair: show original/current anchor, reason and read-only source links; wait or pause/stop. A recorded run link does not release the hold.
- **4b**: Admission is uncertain: show `recovering` with known artifacts; inspect/reconcile the same claim, with no replacement start.
- **4c**: Native owner is rejected/failed/canceled or evidence changes: show attention and the owning run's controls. The batch never automatically skips it; stop remains available.
- **5a**: A concurrent control changed revision: show current state, retain unsent intention visibly and require a fresh explicit action. Receipt replay never undoes a later stop.
- **5b**: Claim won before pause/stop: show the exact admitted member and notice that its artifacts can still appear; follow the existing run for its controls.
- **6a**: Reload or obsolete project response: restore server state by project/batch ID and ignore late older responses.

Keep `UC-start-sdd-activity` registration semantics; add batch-origin links and unchanged approval boundary. Extend `UC-complete-sdd-workflow` with read-only batch ancestry and no second merge owner. `UX-sdd-execution` links batch detail without absorbing its selection/control task.

### Screens

#### Candidates and recommendation

- **A — durable batch panel (recommended)**: A single primary ordered member list moves from execution selection to retained progress. Basis and control summary sit above it; details/owner links expand per row. The panel reopens from a repository batch list after reload. This keeps the bounded 50-member task beside the inspected repository.
- **B — separate selection wizard and batch screen**: A selection step, confirmation step and dedicated progress page give more space but require additional navigation and state recovery. Prefer this only if the bounded panel cannot expose order/holds accessibly.

#### UX-sdd-batch — panel draft

- **element**: panel
- **usecases**: UC-execute-sdd-batch
- **capabilities**: `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control`, `CAP-SDD-runtime-isolation`, `CAP-EXEC-scheduling-maintenance`
- **entry**: Execution selection action in the future milestone preview, or Open batch in the repository's retained batch list.

**Purpose**: Select and follow sequential native SDD work. Before committing, the operator sees exact membership, captured basis, deterministic order, through-Development intent, current/waiting eligibility and unselected prerequisites. Owner approval details are secondary links.

**Content**: The ordered SDD unit list is primary. Repository and milestone basis, completeness and control revision sit above it. Selection confirmation or future-admission controls appear beside that basis. Expanded rows contain prerequisite comparison, claim/PR/run evidence and safe recovery text. Use `modules/hub-ui/src/routes/layout.css` and existing repository controls.

- Repository viewer: project/repository/base ref, initial SHA and latest evaluated SHA/time, milestone ID/path and completeness/limits.
- SDD batch (proposed term): durable identifier, status/revision, selected/waiting/admitted/succeeded counts and through-Development intent.
- SDD unit: exact original PROP ID/path, current phase and canonical SPEC when validated, order, eligible-now or waiting-for-prerequisite label, explicit checkbox before creation only.
- Native SDD activity: per-member Planning/Development effort and catalog preferences, showing inherited defaults and explicit overrides before creation; effective retained preferences remain visible in confirmation and durable row details, subordinate to the ordered list.
- Native SDD activity: current Planning/Development claim, separately timestamped workflow/authority observations and owner links.
- PR run: exact PR/run links and owner-confirmed merged/failed/canceled result, when available.
- SDD batch: Pause future admission, Resume future admission, Stop future admission and Refresh status controls.

**States**:

- `empty`: No executable selection; choose supported members or return to preview. A current nonterminal batch offers Open batch instead of Create.
- `loading`: Announce evaluation/submission, preserve selected basis and pending request ID, disable duplicate mutation; return to repository remains available.
- `selecting`: Show complete graph and unselected rows; waiting entries explicitly promise no start until prerequisites and admission pass. Create remains disabled for empty/invalid selection.
- `confirming`: Show immutable ordered IDs, both phases, effective effort/catalog preferences with inherited-versus-overridden labels, external holds and gate notice. Confirm create or back to selection. Stop confirmation names irrevocable end of future admissions and already-admitted work; confirm or back.
- `running`: Highlight the single claimed member/phase and next wait; inspect owner, refresh or pause/stop future admission.
- `waiting`: Display exact dependency, workflow gate or owner wait. Offer read-only source/owner links, refresh, pause or stop; decisions occur only through owner controls.
- `recovering`: Show durable claim and known artifacts with uncertainty; refresh reconciles it. Pause/stop remains available for future claims; no replacement action exists.
- `paused`: Show future admission paused and any active claim; resume, stop or inspect that owner.
- `attention`: Show failed/rejected/changed-input/canonical-repair cause with exact source/owner links; refresh after repair or stop. No skip/replacement action.
- `stopped`: Label remaining members unexecuted and show already-admitted work until settled; inspect owner or return. Create another selection becomes available only after exclusion is released.
- `completed`: Every member succeeded with exact completed SPEC and confirmed merge evidence; inspect retained results or return.
- `conflict`: Show current revision/basis; reload a fresh preview for stale creation or explicitly retry a valid control against current state. No old selection is silently reused.
- `error`: Safe access/transport/runtime message; retry the same unresolved request or return. Display no successful receipt until established.

**Interactions**:

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open execution selection | UC-execute-sdd-batch 1 | empty | loading | | `CAP-SDD-native-delivery` | Current pinned evidence appears with empty explicit selection. |
| Select/deselect supported member | UC-execute-sdd-batch 2 | selecting | selecting | | `CAP-SDD-native-delivery` | Exact order and waiting/outside prerequisite summary update; no effects occur. |
| Inspect source/prerequisite | UC-execute-sdd-batch 2, 2a, 4a | selecting, waiting, attention | same | `UX-repository` | `CAP-SDD-native-delivery` | Open exact captured/current anchor and comparison. |
| Edit per-member activity preferences | UC-execute-sdd-batch 2 | selecting | selecting | | `CAP-SDD-native-delivery` | Effective Planning/Development effort and catalog choices update; inherited defaults versus explicit overrides remain visible. No execution starts. |
| Review selection | UC-execute-sdd-batch 3 | selecting | confirming | | `CAP-SDD-native-delivery` | Show exact intent, phases, immutable order and separate gates notice. |
| Confirm create | UC-execute-sdd-batch 3, 3a, 3b | confirming | loading | | `CAP-SDD-native-delivery` | Same request yields durable receipt or exact conflict; no duplicate create on response loss. |
| Back from confirmation | UC-execute-sdd-batch 3, 5 | confirming | selecting or prior durable state | | `CAP-SDD-native-delivery` | No create/stop is sent. |
| Open owner execution | UC-execute-sdd-batch 4, 4b, 4c, 5b | running, waiting, recovering, attention, paused, stopped | same | `UX-run-decisions` | `CAP-SDD-workflow-control` | Open existing owner controls without approving or resuming it. |
| Refresh status or reopen batch | UC-execute-sdd-batch 4, 4a, 4b, 6a | all durable states | loading | | `CAP-SDD-native-delivery` | Current revision and exact holds restore; older responses cannot overwrite them. |
| Pause/Resume future admission | UC-execute-sdd-batch 5, 5a, 5b | running, waiting, recovering, attention, paused | loading | | `CAP-SDD-native-delivery` | Revisioned receipt distinguishes future claims from already-admitted effects. |
| Review Stop future admission | UC-execute-sdd-batch 5 | all nonterminal durable states | confirming | | `CAP-SDD-native-delivery` | Name remaining unexecuted members and exact admitted work; offer confirm/back. |
| Confirm Stop future admission | UC-execute-sdd-batch 5, 5a, 5b | confirming | loading | | `CAP-SDD-native-delivery` | Stop receipt is terminal for future claims; current owner is unaffected. |
| Return to preview/repository | UC-execute-sdd-batch 6 | all states | end | back | `CAP-SDD-native-delivery` | Durable batch remains accessible from repository batch list. |

**Register changes**: Add SDD batch as an Operator object, owned by `CAP-SDD-native-delivery`: immutable selected sequential unit intent and controls, excluding Work Plan, native activity and PR execution. Avoid generic batch/job/Work Plan synonyms; candidate code identifiers `SddBatch`, `SddBatchMember`. Register selected order, state/revision/holds, activity preferences, admission claim and retained outcome representations; calls to action Select members, Edit activity preferences, Create batch, Open batch, Pause/Resume/Stop future admission, Refresh status and Inspect owner. Extend SDD unit with waiting exact prerequisite/canonical lineage representations. Keep all approvals on Native SDD activity; keep PR controls on PR run. Add the term to glossary only during Development reconciliation.

## 3. Architecture and Decision Impact

Promote `ADR-sdd-batch-ledger` and restate its clauses in `CAP-SDD-native-delivery` and `ARCH-06-execution`. Describe Project→Batch→shared activity reservation lock order, immutable selection, admission linearization, expected-base seam, recovery checkpoints and retention protection. No separate PR executor or new feature dependency edge is assumed.

## 4. Development Conventions and Governance

Regenerate the typed API client. Preserve owner-specific access/revision fences. Keep components below repository size limits. Create reciprocal CAP/UC/UX links and check draft Step coverage again after reconciliation. Current repository contracts remain unchanged during Planning.

## 5. Before and After

Before: operators individually start eligible native activities; preview selection is local. After: an explicit durable selection retains future intent and progresses one native unit through existing owners, with current prerequisites, gates and uncertain outcomes visible. No numerical performance claim is made.
