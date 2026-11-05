---
id: UX-sdd-execution
title: Run an SDD Spec
summary: "The native execution panel checks runtime and bound-unit readiness before enrolling an existing activity PR and shows related execution links."
area: sdd
element: panel
status: active
usecases:
  - UC-complete-sdd-workflow
  - UC-inspect-repository-documents
capabilities:
  - CAP-SDD-workflow-control
  - CAP-SDD-runtime-isolation
  - CAP-DOC-repository-viewer
---

# [UX-sdd-execution] Run an SDD Spec

## 1. Purpose

- **Primary task**: Check and enroll an existing native spec PR.
- **Facts to commit**: Unit directory, existing PR number, activity effort and readiness for their exact combination.
- **Secondary items**: Runtime diagnostics and related executions sit beside the registration result; stages and decisions open in Pipeline Runs.

## 2. Content

Readiness and enrollment controls are primary. Runtime status is a separate
check, and related execution links remain read-only supporting context.

- SDD unit (directory input; follows a recognized viewer selection).
- PR run (existing positive PR number and activity effort).
- Native SDD activity (runtime profile/isolation/bundle status).
- Native SDD activity (readiness head, CLI version and warnings).
- Native SDD activity (registered execution link to `UX-run-decisions`).
- PR run (recent unit-related execution rows, lineage and external PR links).

Start execution is enabled only after readiness for the current project/unit/PR
combination and is disabled after that combination registers successfully. A
changed selection invalidates the old readiness. Related-run lookup has its own
loading/empty/error state and ignores responses for an old selection.

## 3. States

- **populated**: Enter the unit and PR, then check readiness; inspect related executions when present.
- **empty**: A unit with no related runs states this explicitly and offers readiness checking.
- **loading**: Runtime/readiness/registration requests disable competing inputs; related-link loading is announced separately.
- **ready**: A matching readiness result enables Start execution.
- **registered**: The same combination cannot be submitted again; Open execution & decisions follows the retained run.
- **error**: Runtime, readiness/start and related-link failures are shown separately; correct the input or use the applicable retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Check runtime | global: diagnose the server-selected native execution runtime | populated | loading |  | `CAP-SDD-runtime-isolation` | Profile/isolation/bundle information or an unavailable/error diagnostic appears. |
| Check readiness | `UC-complete-sdd-workflow` 1 | populated | loading |  | `CAP-SDD-workflow-control` | The inspected head, CLI version and warnings appear or a setup/refusal error is shown. |
| Start execution | `UC-complete-sdd-workflow` 1 | ready | loading |  | `CAP-SDD-workflow-control` | Successful registration offers the retained execution link and disables resubmitting that combination. |
| Open execution & decisions | `UC-complete-sdd-workflow` 3 | registered | populated | `UX-run-decisions` | `CAP-SDD-workflow-control` | The selected run opens in its decision dialog. |
| Open related execution | `UC-inspect-repository-documents` 6 | populated | populated | `UX-run-decisions` | `CAP-DOC-repository-viewer` | The recorded project-scoped run and decisions open without starting work. |
| Retry related executions | `UC-inspect-repository-documents` 5c | error | loading |  | `CAP-DOC-repository-viewer` | The selected unit’s related runs are requested again. |

## 5. Evidence

- [SddExecution.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddExecution.svelte).
- [SddRunLinks.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.svelte).
- [SddExecution.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddExecution.integration.test.ts); test assertions were inspected.
- [SddRunLinks.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.
