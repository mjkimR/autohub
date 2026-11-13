---
id: TASKS-hub-ui-color-system
spec: SPEC-hub-ui-color-system
plan: PLAN-hub-ui-color-system
---

# Task Breakdown: `SPEC-hub-ui-color-system` Rank operator attention in the hub-ui color system

Run tasks in order: Task 2 needs the `attention` Badge variant from Task 1, and Task 3 renders `RunStateBadge` from
Task 2. Task 4 and Task 5 depend only on Task 1. Section numbers refer to `PLAN-hub-ui-color-system`. Every touched
authored file must end with zero `shadcn/*` warnings; `badge.svelte` is a generated primitive outside that lint.

## Phase 1: Implementation

- [x] **Task 1**: Tokens, `attention` Badge variant, document shell and the contrast test
  - **_Boundary**: `modules/hub-ui/src/routes/layout.css`, `modules/hub-ui/src/routes/layout-contrast.test.ts`, `modules/hub-ui/src/lib/components/ui/badge/badge.svelte`, `modules/hub-ui/src/app.html`, `modules/hub-ui/src/lib/assets/favicon.svg`
  - _Requirements: AC-01, AC-02, AC-03, AC-06_
  - Apply the plan section 3.1 token table literally in `:root` and `.dark`, and register the four attention tokens in `@theme inline`.
  - Add the `attention` variant of section 3.2; leave other variant strings unchanged.
  - Change `app.html` selection and `favicon.svg` per section 3.6.
  - Write the contrast test of section 3.7 covering every AC-06 pair in both themes.
  - **Verification**: `just test-ui` passes, including `layout-contrast.test.ts`; `just check` exits 0; `rg -n "6366f1" modules/hub-ui/src` returns nothing.

- [x] **Task 2**: Run state presentation and `RunStateBadge` at the three run-owned call sites, with unit tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.ts`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/presentation.test.ts`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunStateBadge.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunRow.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.svelte`, `modules/hub-ui/src/lib/features/project-management/repositories/SddRunLinks.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/PipelineRunsView.integration.test.ts`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.integration.test.ts`
  - _Requirements: AC-04, AC-11_
  - Add `getRunStatePresentation` and the AC-04 mapping (section 3.3); `getStateBadgeVariant` delegates to it and no state returns `warning`.
  - Create `RunStateBadge.svelte` and use it in the three files; remove the inline state icons and now-unused imports from `PipelineRunRow.svelte`.
  - Edit the two integration tests only if a label or representation assertion must change; keep their interactions.
  - **Verification**: `just test-ui` passes, including `presentation.test.ts` for all nine states; `npx --prefix modules/hub-ui eslint` on the touched files shows no `shadcn/` warning.

- [x] **Task 3**: Dashboard PR run summary and Decisions inbox status, with integration tests
  - **_Boundary**: `modules/hub-ui/src/lib/features/dashboard/DashboardView.svelte`, `modules/hub-ui/src/lib/features/dashboard/dashboard.svelte.ts`, `modules/hub-ui/src/lib/features/dashboard/DashboardView.integration.test.ts`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/DecisionInbox.integration.test.ts`
  - _Requirements: AC-05, AC-07, AC-11, AC-12_
  - Apply section 3.4: the `needsYouBreakdown` getter, neutral tiles, the three Needs-you cases with `data-attention`, the breakdown caption, the unfiltered `/projects/runs` link above zero, muted section-header icons and `RunStateBadge` in the recent-runs list.
  - Apply section 3.5: the three settled status badges, the attention left rule with `data-attention` on both attention rows, the filter option labels, and `outline` Review, Retry and Retry review buttons.
  - Add test cases for Needs-you `> 0` (count, breakdown, link `href`), `0` ("No failed or held runs", no link) and unavailable (`—`, no link), and for the three inbox labels, the `data-attention` rows and the filter option texts.
  - **Verification**: `just test-ui` passes; `npx --prefix modules/hub-ui eslint` on the four files shows no `shadcn/` warning; neither Svelte file exceeds its size-preset limit.

- [x] **Task 4**: Remove decorative primary and raw palette colors
  - **_Boundary**: `modules/hub-ui/src/lib/components/shared/AppShell.svelte`, `modules/hub-ui/src/lib/components/shared/JsonSchemaForm.svelte`, `modules/hub-ui/src/lib/features/auth/login/LoginView.svelte`, `modules/hub-ui/src/lib/features/configuration/ai-catalogs/AICatalogsView.svelte`, `modules/hub-ui/src/lib/features/configuration/notifications/NotificationsView.svelte`, `modules/hub-ui/src/lib/features/configuration/system-configs/SystemConfigsView.svelte`, `modules/hub-ui/src/lib/features/dashboard/DashboardHealth.svelte`, `modules/hub-ui/src/lib/features/execution/task-specs/TaskSpecsView.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttachPullRequestDialog.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/AttemptHistoryDialog.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/EnrollPullRequestDialog.svelte`, `modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddRunPanel.svelte`, `modules/hub-ui/src/lib/features/project-management/projects/ProjectConnectionCheckDialog.svelte`, `modules/hub-ui/src/lib/features/project-management/projects/ProjectOverview.svelte`, `modules/hub-ui/src/lib/features/scheduling/schedule-configs/ScheduleConfigsView.svelte`, `modules/hub-ui/src/lib/features/scheduling/schedule-jobs/ScheduleJobsView.svelte`
  - _Requirements: AC-08, AC-09_
  - Apply every item of section 3.6 except `app.html` and `favicon.svg` (Task 1).
  - Change classes only; keep markup structure, text and interactions, except the deleted header chip and login backdrop elements.
  - **Verification**: `rg -n "Svelte 5 Runes|bg-primary/10|hover:border-primary|shadow-primary|emerald|amber" modules/hub-ui/src --glob '!**/components/ui/**'` returns nothing; `just test-ui` passes; `npx --prefix modules/hub-ui eslint` on the touched files shows no `shadcn/` warning.

- [x] **Task 5**: Document the attention token and color roles
  - **_Boundary**: `modules/hub-ui/README.md`, `docs/steering/visual-style.md`
  - _Requirements: AC-03, AC-10_
  - Create `docs/steering/visual-style.md` per plan section 5 (frontmatter `title` and English `summary` only; roles, not values).
  - Update the README Design-system lint section: `attention` among status colors and Badge variants, with a pointer to the steering file.
  - **Verification**: `uv run --no-active devkit rules check docs/steering/visual-style.md` reports no violation; `git diff --check` is clean.

- [x] **Task 6**: Final verification of the whole change
  - **_Boundary**: none (checks only; fixes return to the owning task's boundary)
  - _Requirements: AC-10, AC-11_
  - **Verification**: from the repository root, `just lint`, `just check` and `just test-ui` exit 0; `git diff --stat main -- modules/hub-ui/eslint.config.js` is empty; `npx --prefix modules/hub-ui eslint` over every file in Tasks 1-4 (except `badge.svelte`) reports no `shadcn/` warning.
