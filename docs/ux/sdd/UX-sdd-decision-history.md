---
id: UX-sdd-decision-history
title: SDD Approval Activity
summary: "The approval-activity panel lists native decisions and their publication outcomes, including safe reconciliation of an uncertain saved request."
area: sdd
element: panel
status: active
usecases:
  - UC-decide-sdd-proposal
  - UC-complete-sdd-workflow
capabilities:
  - CAP-SDD-native-delivery
  - CAP-SDD-workflow-control
---

# [UX-sdd-decision-history] SDD Approval Activity

## 1. Purpose

- **Primary task**: Inspect a recorded native decision and its publication outcome.
- **Facts to commit**: Action, actor, time, feedback, inspected head/base and publication state.
- **Secondary items**: The panel initially shows five rows; expanded rows and revision details remain secondary.

## 2. Content

Decision history is primary; each publication status stays attached to its own
decision so a Git publication is not confused with applied approval.

- Native SDD activity (up to 100 latest decision rows; newest history is loaded).
  - Native SDD activity (action label, actor, timestamp and optional feedback).
  - Native SDD activity (inspected head/base disclosure).
  - Native SDD activity (publication state and optional Reconcile decision).

Preparing, prepared and uncertain publication states explain that success is
unconfirmed. Human saved requests can expose reconciliation; automatic policy
decisions instead direct the operator to resume inspection. A published result
with applied false explicitly states that approval was not applied.

The Check request outcome action selects that exact historical resume request in the parent retained outcome region. Selection changes the displayed read identity without replacing any unresolved mutation intent.

## 3. States

- **populated**: Inspect recorded decisions, expand history or reveal inspected revisions.
- **empty**: No decisions exist; return to the current request/evidence controls.
- **loading**: History announces loading; wait for the current run revision.
- **error**: A history error asks for refresh; failed reconciliation keeps its own error visible.
- **busy**: Reconciliation disables its control until the saved request settles.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Refresh approval history | `UC-decide-sdd-proposal` 6, `UC-complete-sdd-workflow` *b | populated | loading |  | `CAP-SDD-workflow-control` | Decision/publication rows are loaded again. |
| Reconcile decision | `UC-decide-sdd-proposal` 5b, `UC-decide-sdd-proposal` 6a | populated | busy |  | `CAP-SDD-native-delivery` | The exact saved request is retried; history and parent run evidence refresh. |
| Show all / fewer decisions | global: inspect bounded native approval history | populated | populated |  | `CAP-SDD-workflow-control` | The visible row count changes. |
| Inspected revision | global: inspect the evidence basis of a retained decision | populated | populated |  | `CAP-SDD-workflow-control` | The decision’s head/base values are disclosed. |

| Check request outcome | `UC-complete-sdd-workflow` *b, `UC-decide-sdd-proposal` 3d | populated | populated | `UX-run-decisions` | `CAP-SDD-workflow-control` | Parent shows the exact historical request outcome; the action performs no continuation. |

## 5. Evidence

- [SddDecisionHistory.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddDecisionHistory.svelte).
- [SddPublicationStatus.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddPublicationStatus.svelte).

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
