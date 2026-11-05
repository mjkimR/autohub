---
id: UX-sdd-workflow-request
title: SDD Workflow Request
summary: "The workflow-request panel presents the current native request and keeps proposal decisions, worker answers and other workflow choices distinct."
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

# [UX-sdd-workflow-request] SDD Workflow Request

## 1. Purpose

- **Primary task**: Answer the current native workflow request.
- **Facts to commit**: Request identity, prompt, eligible/recommended options, inspected head and the meaning of the selected action.
- **Secondary items**: Integration approval stays in `UX-sdd-run`; decision/publication history stays in `UX-sdd-decision-history`.

## 2. Content

The first current request is primary. Eligible choices and its note/decision
editor precede the action buttons; explanation below states how the answer is
published and whether the request remains open.

- Native SDD activity (current request ID, kind, title, prompt and optional context).
- Native SDD activity (eligible radio choices and recommendation marker).
- Native SDD activity (note or outside-options worker decision).
- SDD unit (inspected proposal head; for a plan-accept request).

The panel appears for a paused/blocked run with an applicable request. It excludes
the dev-integration gate. Worker questions expose Record answer but no Decline or
Defer; proposal rejection requires a reason; other requests can expose Decline
and Defer with text explaining that these leave the request open.

## 3. States

- **populated**: Review the current request and choose an eligible answer.
- **empty**: No applicable request is rendered; inspect the parent’s next-action panel.
- **busy**: Recording disables the request controls; wait for refreshed evidence.
- **error**: The action error remains visible; inspect/refresh the current request before retrying.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Accept proposal | `UC-decide-sdd-proposal` 2 | populated | busy |  | `CAP-SDD-native-delivery` | The decision is authored for the inspected head and current evidence reloads. |
| Reject proposal | `UC-decide-sdd-proposal` 2a | populated | busy |  | `CAP-SDD-native-delivery` | A nonblank reason is required; publication outcome or refusal is shown. |
| Record answer | `UC-complete-sdd-workflow` 3b | populated | busy |  | `CAP-SDD-workflow-control` | The UI explains that the worker question remains open until the agent publishes its answer envelope. |
| Confirm choice / Approve | `UC-complete-sdd-workflow` 3c | populated | busy |  | `CAP-SDD-workflow-control` | The selected workflow direction is retained and refreshed evidence is shown. |
| Decline / Defer decision | `UC-complete-sdd-workflow` 3c | populated | busy |  | `CAP-SDD-workflow-control` | The request remains open; these actions do not stop the run or withdraw integration authority. |

## 5. Evidence

- [SddWorkflowRequests.svelte](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddWorkflowRequests.svelte).
- [SddWorkflowRequests.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddWorkflowRequests.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
