---
id: UX-sdd-execution
title: Run an SDD Spec
summary: "The native execution panel previews a bound unit's first stage, existing waits, approval policy and safe diagnostics before enrolling its existing activity PR."
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
- **Facts to commit**: Unit directory, existing PR number, activity effort, registration eligibility and initial stage/waits for their exact inspected combination.
- **Secondary items**: Runtime diagnostics and related executions sit beside the registration result; stages and decisions open in Pipeline Runs.

## 2. Content

Readiness and enrollment controls are primary. Runtime status is a separate
check, and related execution links remain read-only supporting context.

- SDD unit (directory input; follows a recognized viewer selection).
- PR run (existing positive PR number and activity effort).
- Native SDD activity (runtime check line: host sandbox and `ok`/unavailable result, then the default-branch head's repository lock as `ready` with its short identity and bundles, `installing; check again shortly`, `unavailable` with its catalog detail, or `not checked` without a project connection).
- Native SDD activity (Execution preview with registration eligibility, inspected head/CLI version, next reported stage, existing problems/questions/requests and informational approval policy).
- Native SDD activity (structured diagnostic code/severity, responsibility category, summary, next step, static file targets and read-only retry guidance; unmatched historical warnings remain visible).
- Native SDD activity (registered execution link to `UX-run-decisions`).
- PR run (recent unit-related execution rows, lineage and external PR links).

The runtime check line is a status message when the host probe passes and the
repository lock is ready, installing or not checked; it becomes an alert when the
host probe fails or the repository lock is unavailable.

Start execution is enabled only after readiness for the current project/unit/PR
combination and is disabled after that combination registers successfully. A
changed selection invalidates the old readiness and preview. Late successful or failed responses for another selection cannot replace its context. Related-run lookup has its own
loading/empty/error state and ignores responses for an old selection.

The preview distinguishes Eligible to register from existing workflow input. An eligible unit can register while questions, holds or approvals remain pending; registration grants none of their authority. Approval policy is a secondary disclosure, and only a current request/gate labels an active approval wait. A missing stage says No next stage reported; a complete workflow says Workflow complete. Failed readiness keeps safe diagnostics visible but enables no registration. Guidance has no retry or command-execution control.

Milestone subset inspection belongs to `UX-sdd-milestone-preview`. Its result supplies neither this panel's PR number nor permission to enroll or resume a run.

## 3. States

- **populated**: Enter the unit and PR, then check readiness; inspect related executions when present.
- **empty**: A unit with no related runs states this explicitly and offers readiness checking.
- **loading**: Runtime/readiness/registration requests disable competing inputs; related-link loading is announced separately.
- **ready**: A matching readiness result enables Start execution and shows Execution preview; any existing workflow wait is disclosed separately.
- **registered**: The same combination cannot be submitted again; Open execution & decisions follows the retained run.
- **error**: Runtime, readiness/start and related-link failures are shown separately; correct the input or use the applicable retry.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Check runtime | global: diagnose the host sandbox and the project's repository-locked runtime | populated | loading |  | `CAP-SDD-runtime-isolation` | The host sandbox result and the repository lock state (ready with identity and bundles, installing, or unavailable with its detail) appear; a request failure appears as an error. |
| Check readiness | `UC-complete-sdd-workflow` 1 | populated | loading |  | `CAP-SDD-workflow-control` | Registration eligibility, inspected head, first stage, current waits, approval policy and safe diagnostics appear, or a setup/refusal error retains its safe guidance. |
| Start execution | `UC-complete-sdd-workflow` 1 | ready | loading |  | `CAP-SDD-workflow-control` | Successful registration offers the retained execution link and disables resubmitting that combination. |
| Open execution & decisions | `UC-complete-sdd-workflow` 3 | registered | populated | `UX-run-decisions` | `CAP-SDD-workflow-control` | The selected run opens in its decision dialog. |
| Open related execution | `UC-inspect-repository-documents` 6 | populated | populated | `UX-run-decisions` | `CAP-DOC-repository-viewer` | The recorded project-scoped run and decisions open without starting work. |
| Retry related executions | `UC-inspect-repository-documents` 5c | error | loading |  | `CAP-DOC-repository-viewer` | The selected unit’s related runs are requested again. |

## 5. Evidence

- [SddExecution.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddExecution.svelte).
- [sdd-execution.svelte.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/sdd-execution.svelte.ts) (runtime check line).
- [SddReadinessPreview.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddReadinessPreview.svelte).
- [SddRunLinks.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.svelte).
- [SddExecution.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddExecution.integration.test.ts); test assertions were inspected.
- [SddRunLinks.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.integration.test.ts); test assertions were inspected.

This description is derived from source inspection. It does not claim a browser
walkthrough, a fresh test execution or a live provider result.

## 6. Sequential selection context

The separate adjacent `UX-sdd-batch` panel owns execution selection and retained batch status. Its Inspect native owner link opens `UX-run-decisions` for an existing activity. This panel continues to register one existing PR; batch intent and preview results do not populate or approve its enrollment inputs.
