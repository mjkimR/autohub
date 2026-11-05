---
id: UX-connection-tests
title: AI Connection Tests
summary: "Start and inspect isolated provider connection tests, their configuration applicability and independently retained cleanup evidence."
area: projects
element: panel
status: active
usecases:
  - UC-verify-project-connection
capabilities:
  - CAP-CONN-connection-verification
  - CAP-AGENT-catalog-admission
---

# [UX-connection-tests] AI Connection Tests

## 1. Purpose

- **Primary task**: verify an AI catalog against one Project connection.
- **Facts to commit**: selected catalog, recipe, configured/manual prerequisites and the isolated PR/cleanup effects.
- **Secondary items**: each retained result carries its evidence links, continuation controls and conditional ownership review.

## 2. Content

The selected recipe and Start PR test control precede retained results. Verification and cleanup appear separately on every result card.

- AI catalog (recipe selector): provider, readiness and recipe requirements, with allowed setup links.
- Connection test (result card): catalog snapshot, phase, status, detail, creation time and changed-configuration warning.
  - Connection test (evidence): verified push, PR/CI links, provider metadata and cleanup status/warnings/errors.
  - Connection test (cleanup review): candidate PR heads, confirmation checkbox and review notes when reconciliation is available.
- Next actions: Start PR test, Check / continue now, Cancel test and conditional Review cleanup.

Results refresh every ten seconds. The selected catalog is retained while an uncertain start is retried with its original request identity.

## 3. States

- **populated**: choose a ready recipe and inspect retained results; continue or cancel eligible work.
- **empty**: no supported catalogs or no prior PR test; configure a supported catalog or start a ready recipe.
- **loading**: initial tests/options load; starting is disabled.
- **error**: load failure offers Retry; mutation errors appear as toasts.
- **running**: phase and cancellation-request state remain visible while Start PR test is disabled.
- **reviewing**: cleanup review requires a remote-stop/unrelated-work confirmation and nonempty notes before submission; Back leaves review without submitting.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Choose catalog and inspect requirements | `UC-verify-project-connection` 1, `UC-verify-project-connection` 1a | populated, empty | populated |  | `CAP-CONN-connection-verification` | Recipe readiness and configured/missing/manual prerequisites are shown. |
| Start PR test | `UC-verify-project-connection` 2, `UC-verify-project-connection` 3, `UC-verify-project-connection` 3a, `UC-verify-project-connection` 3b | populated | running |  | `CAP-CONN-connection-verification` | The accepted start queues a test and reloads; conflicts/refusals produce a toast. |
| Check / continue now or scheduled refresh | `UC-verify-project-connection` 4, `UC-verify-project-connection` 5, `UC-verify-project-connection` 6, `UC-verify-project-connection` 7 | running, populated | running, populated |  | `CAP-CONN-connection-verification` | Phase, verified SHA, evidence and independent cleanup result refresh. |
| Read waiting / uncertain / failed results | `UC-verify-project-connection` 4a, `UC-verify-project-connection` 4b, `UC-verify-project-connection` 4c, `UC-verify-project-connection` 5a, `UC-verify-project-connection` 5b, `UC-verify-project-connection` 6a, `UC-verify-project-connection` 6b | running, populated | populated |  | `CAP-CONN-connection-verification` | Retained detail and cleanup evidence distinguish an unresolved wait from verified success. |
| Cancel test / observe deadline result | `UC-verify-project-connection` 4d | running | populated |  | `CAP-CONN-connection-verification` | Cancellation request or terminal timeout is visible; cleanup is still reported separately. |
| Request refuses an unknown project/test | `UC-verify-project-connection` *a | populated | error |  | `CAP-CONN-connection-verification` | The refusal is shown without a new test result. |
| Review cleanup / confirm review / Back | global: reconcile terminal cleanup ownership without altering the test outcome | populated, reviewing | reviewing, populated |  | `CAP-CONN-connection-verification` | Review records a confirmation and note; cleanup rechecks remote evidence before completion. |

## 5. Evidence

Source inspection:
- `modules/hub-ui/src/lib/features/project-management/projects/ConnectionTestsPanel.svelte`
- `modules/hub-ui/src/lib/features/project-management/projects/ConnectionTestRecovery.svelte`

The content and transitions are derived from source inspection. This document
does not assert a browser walkthrough or live GitHub/provider verification.
