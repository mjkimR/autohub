---
id: UX-sdd-proposals
title: SDD Proposals
summary: "The proposals panel lists native proposal state on an explicit base branch and offers eligible Planning, Development and proposal-review actions."
area: sdd
element: panel
status: active
usecases:
  - UC-start-sdd-activity
  - UC-decide-sdd-proposal
capabilities:
  - CAP-SDD-native-delivery
---

# [UX-sdd-proposals] SDD Proposals

## 1. Purpose

- **Primary task**: Start or inspect a native proposal activity.
- **Facts to commit**: Base branch, proposal identity/status, recommendation and available activity actions.
- **Secondary items**: Detailed acceptance review opens the run decisions dialog; branch PR links open GitHub.

## 2. Content

The proposal list is primary. Base branch and activity-effort controls apply to
subsequent load/start actions. Each row keeps its actions beside its proposal.

- SDD unit (proposal title, ID, display status and optional note).
- Native SDD activity (Planning/Development recommendations and optional override).
- PR run (recorded run state and plan/dev PR links).
- SDD unit (inline rejection-reason editor; when Reject is selected).
- `UX-run-decisions` (modal reached by Review & accept).

Only server-offered actions render. A blank effort uses the proposal recommendation.
Request identities are reused for the same action/base/effort or decision intent;
a failed action retains its error rather than claiming remote rollback.

## 3. States

- **populated**: Review proposals and use an offered activity action.
- **empty**: No proposals were returned on the chosen base; change the base and refresh.
- **loading**: Loading proposals is announced; wait for the selected base result.
- **busy**: One proposal action is pending and competing action buttons are disabled.
- **rejecting**: An inline reason editor requires nonblank text before Reject proposal.
- **error**: A load/action error is visible; inspect remote artifacts or refresh before retrying.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh | `UC-start-sdd-activity` 1 | populated | loading |  | `CAP-SDD-native-delivery` | Proposal state is reloaded for the entered base. |
| Start review / Start development | `UC-start-sdd-activity` 1 | populated | busy |  | `CAP-SDD-native-delivery` | A started-activity message appears and proposal/run state reloads. |
| Review & accept | `UC-decide-sdd-proposal` 1 | populated | populated | `UX-run-decisions` | `CAP-SDD-native-delivery` | The linked PR run opens directly in decisions. |
| Reject… / Reject proposal | `UC-decide-sdd-proposal` 2a | populated | rejecting |  | `CAP-SDD-native-delivery` | A reason editor precedes submission; the decision result or failure is shown. |
| Open plan/dev PR | global: inspect the activity branch in GitHub | populated | populated | end | `CAP-SDD-native-delivery` | The associated external PR opens. |

## 5. Evidence

- [SddProposals.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddProposals.svelte).
- [SddProposals.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddProposals.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
