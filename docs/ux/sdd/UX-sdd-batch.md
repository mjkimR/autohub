---
id: UX-sdd-batch
title: Sequential milestone execution
summary: "The repository panel confirms immutable native SDD selections and reopens retained batch status, exact activity owners and future-admission controls."
area: sdd
element: panel
status: active
usecases:
  - UC-execute-sdd-batch
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
  - CAP-EXEC-scheduling-maintenance
---

# [UX-sdd-batch] Sequential milestone execution

## 1. Purpose

Select and follow sequential native SDD work. Before committing, the operator sees exact membership, captured basis, deterministic order, through-Development intent, current/waiting eligibility and unselected prerequisites. Owner approval details are secondary links.

## 2. Content

The ordered SDD unit list is primary. Repository and milestone basis, completeness and control revision sit above it. Selection confirmation or future-admission controls appear beside that basis. Expanded retained rows contain the original path/current SPEC identity, immutable preferences, claim/PR/run evidence and safe recovery text. The adjacent `UX-sdd-milestone-preview` supplies captured graph, prerequisite and source-link inspection. `UX-run-decisions` and its native owner panels supply detailed workflow, authority and merge-result inspection. Use `modules/hub-ui/src/routes/layout.css` and existing repository controls.

- Repository viewer: selected milestone/ref/captured SHA before creation; retained batch initial SHA and latest evaluated SHA/time afterward. Full captured graph, source links, milestone path and completeness/limits stay in the adjacent `UX-sdd-milestone-preview`.
- SDD batch: durable identifier, status/revision, selected/waiting/admitted/succeeded counts and through-Development intent.
- SDD unit: exact original PROP ID/path, current phase and canonical SPEC when validated, order, eligible-now or waiting-for-prerequisite label, explicit checkbox before creation only.
- Native SDD activity: per-member Planning/Development effort and catalog preferences, showing inherited defaults and explicit overrides before creation; effective retained preferences remain visible in confirmation and durable row details, subordinate to the ordered list.
- Native SDD activity: current Planning/Development claim with in-flight/uncertain/settled presentation, safe uncertainty reason/time and exact owner links. Detailed separately timestamped workflow/authority observations stay in the existing owner dialog.
- PR run: known exact PR/run links, retained branch and initial candidate SHA. Detailed confirmed merge evidence opens in its existing native owner dialog.
- SDD batch: Pause future admission, Resume future admission, Stop future admission and Refresh status controls.

## 3. States

- `empty`: No executable selection; choose supported members or return to preview. A current nonterminal batch offers Open batch instead of Create.
- `loading`: Announce evaluation/submission, preserve selected basis and pending request ID, disable duplicate mutation; return to repository remains available.
- `selecting`: Show unselected member rows beside the captured preview graph; waiting entries explicitly promise no start until prerequisites and admission pass. Create remains disabled for empty/invalid selection.
- `confirming`: Show immutable ordered IDs, both phases, effective effort/catalog preferences with inherited-versus-overridden labels, external holds and gate notice. Confirm create or back to selection. Stop confirmation names irrevocable end of future admissions and already-admitted work; confirm or back.
- `running`: Show the ordered members, their phases/states and safe batch detail; inspect owner, refresh or pause/stop future admission.
- `waiting`: Display safe dependency or owner-wait detail and retained identities. Inspect captured prerequisites/source links in the adjacent preview and native workflow gates through owner links; refresh, pause or stop future admission. Decisions occur only through owner controls.
- `recovering`: Show durable claim and known artifacts with uncertainty; Refresh status reads maintenance-produced reconciliation results; it performs no admission or owner continuation. Pause/stop remains available for future claims; no replacement action exists.
- `paused`: Show future admission paused and any active claim; resume, stop or inspect that owner.
- `attention`: Show failed/rejected/changed-input/canonical-repair cause with exact source identities and available owner links; inspect after repair, explicitly resume future admission where appropriate, or stop. Refresh alone only reads state. No skip/replacement action.
- `stopped`: Keep the stopped status and original member states visible, with the notice that remaining members stay unexecuted and admitted work can still settle; inspect owner or return. Create another selection becomes available only after exclusion is released.
- `completed`: Every member succeeded with exact completed SPEC and confirmed merge evidence; inspect retained results or return.
- `conflict`: Show current revision/basis; reload a fresh preview for stale creation or explicitly retry a valid control against current state. No old selection is silently reused.
- `error`: Safe access/transport/runtime message; retry the same unresolved request or return. Display no successful receipt until established.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open execution selection | `UC-execute-sdd-batch` 1 | empty | loading | | `CAP-SDD-native-delivery` | Current pinned evidence appears with empty explicit selection. Retained lookup is available without a preview. |
| Select/deselect supported member | `UC-execute-sdd-batch` 2 | selecting | selecting | | `CAP-SDD-native-delivery` | Exact order and waiting/outside prerequisite summary update; no effects occur. |
| Inspect captured prerequisites in the adjacent preview | `UC-execute-sdd-batch` 2 | selecting, waiting, attention | same | `UX-sdd-milestone-preview` | `CAP-SDD-native-delivery` | The adjacent preview owns graph/source inspection; retained batch rows disclose source identities and safe detail rather than a second source-navigation control. |
| Edit per-member activity preferences | `UC-execute-sdd-batch` 2 | selecting | selecting | | `CAP-SDD-native-delivery` | Effective Planning/Development effort and catalog choices update; inherited defaults versus explicit overrides remain visible. No execution starts. |
| Review selection | `UC-execute-sdd-batch` 3 | selecting | confirming | | `CAP-SDD-native-delivery` | Show exact intent, phases, immutable order and separate gates notice. |
| Confirm create | `UC-execute-sdd-batch` 3 | confirming | loading | | `CAP-SDD-native-delivery` | Same request yields durable receipt or exact conflict; no duplicate create on response loss. |
| Back from confirmation | `UC-execute-sdd-batch` 3 | confirming | selecting or prior durable state | | `CAP-SDD-native-delivery` | No create/stop is sent. |
| Open owner execution | `UC-execute-sdd-batch` 4 | running, waiting, recovering, attention, paused, stopped | same | `UX-run-page` | `CAP-SDD-workflow-control` | The owner run's page opens at its Decisions section without approving or resuming it. |
| Load retained batches, Refresh status or reopen batch | `UC-execute-sdd-batch` 4 | all durable states | loading | | `CAP-SDD-native-delivery` | Explicit GET lookup restores current revision and retained holds; older responses cannot overwrite them. It reads maintenance-produced results without reconciling or continuing work. |
| Pause/Resume future admission | `UC-execute-sdd-batch` 5 | running, waiting, recovering, attention, paused | loading | | `CAP-SDD-native-delivery` | Revisioned receipt distinguishes future claims from already-admitted effects. |
| Review Stop future admission | `UC-execute-sdd-batch` 5 | all nonterminal durable states | confirming | | `CAP-SDD-native-delivery` | Name remaining unexecuted members and exact admitted work; offer confirm/back. |
| Confirm Stop future admission | `UC-execute-sdd-batch` 5 | confirming | loading | | `CAP-SDD-native-delivery` | Stop receipt is terminal for future claims; current owner is unaffected. |
| Return to preview/repository | `UC-execute-sdd-batch` 6 | all states | end | back | `CAP-SDD-native-delivery` | Durable batch remains accessible from repository batch list. |


## 5. Evidence

`modules/hub-ui/src/lib/features/project-management/repositories/SddBatch.svelte` and `sdd-batches.svelte.ts` implement the panel. Their adjacent UI tests cover exact selection/order, immutable preferences, response loss, retained claim/owner disclosure and stale-response refusal. Check execution is recorded separately in `SPEC-sdd-milestone-execution`; no live browser or deployment evidence is claimed.
