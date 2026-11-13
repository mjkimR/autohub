---
id: UX-attention
title: Attention landing
summary: "Triage every owed item across projects and object types at the console root, grouped by consequence, and follow each item's one primary action to the owner screen that resolves it."
area: delivery
element: screen
status: active
usecases:
  - UC-resolve-run-question
  - UC-deliver-pull-request
  - UC-execute-work-plan
  - UC-execute-sdd-batch
  - UC-verify-project-connection
capabilities:
  - CAP-PR-owed-items
  - CAP-PR-operator-decisions
  - CAP-PR-pull-request-delivery
  - CAP-WORK-work-plan-execution
  - CAP-SDD-workflow-control
  - CAP-CONN-connection-verification
---

# [UX-attention] Attention landing

## 1. Purpose

- **Primary task**: see what waits for the operator across projects and open the place where each item is resolved.
- **Facts to commit**: per owed item its cause, subject and project, how long it has waited and its one primary
  action; the number of counted owed items ("Needs you") and how many of each kind; a held AI catalog that stops a run.
- **Secondary items**: resolving happens on the owner screens (`UX-run-page`, `UX-decision-inbox`, `UX-work-plans`,
  `UX-sdd-batch`, `UX-connection-tests`); service health and delivery statistics are on `UX-dashboard` (System ›
  Health); the decision-only worklist and exact notice links stay on `UX-decision-inbox`.

## 2. Content

At `/`, inside `UX-app-shell`. The owed-item groups are primary; the title, filter and Refresh sit above them. The
list reads `GET /api/v1/owed-items` (`CAP-PR-owed-items`) in its (`waiting_since`, `key`) order, at most 100 items per
page; it adds no per-row read. Group sizes and the summary reuse the shell's owed counts store. On mount the landing
asks that store for one fresh read past the shell's navigation throttle, so groups and summary agree with the rows;
the read stays single-flight, so a shell read already in flight is reused rather than repeated.

- Owed item (summary, beside the title): "N items need you." from the shell counts while no project is chosen; hidden
  at zero, while unknown, under a project filter or while the empty state shows.
- Project connection (filter): "All projects" or one project; the choice is the `?project=<projectId>` query, so
  project screens link to their slice of the landing (`/?project=<id>`) and the choice survives reload.
- Owed item (groups), in order of consequence; a kind with no loaded item is left out:
  1. Decisions (`decision`), 2. Held PR runs (`stopped-run`), 3. Work Plans to review (`work-plan-proposed`),
  4. Work Item recovery, 5. Work Item replacement, 6. Work Items needing attention, 7. SDD batches
  (`sdd-batch-attention`), 8. Connection-test cleanup, and last 9. Failed PR runs (`failed-run`).
  - Group heading: the kind label and its count. Counted kinds carry the `attention` Badge; on a screen made only of
    owed items, attention marks each group once and rows stay neutral, so the list never turns into a dense amber
    block (`docs/steering/visual-style.md`). While more pages remain, the count is the kind's total from the shell
    counts when known and no project is chosen, and "N shown" follows when fewer rows are loaded than the total. Once
    every page is loaded, or without known counts, the count is the loaded rows and "N shown" is hidden. The badge's
    accessible text names the kind, for example "5 decisions".
  - Failed PR runs: a quiet section after Load more, with a neutral `outline` count and "Not counted as owed. Inspect
    when convenient."; it carries no attention weight.
  - Owed item (row): the cause as the row's first line; below it the subject title when present, the project name as
    an in-app link to `UX-project-detail`, and "Waiting <age>" with the exact time as a tooltip; one primary action
    (secondary-weight button with the owner's label, its accessible name adds the subject) deep-linking to the owner:
    - Decision: the run page Decisions section (`/projects/<id>/runs/<run>#decisions`), or `UX-decision-inbox` when
      the item names no run.
    - Held PR run: the run page; failed PR run: the run page Next step section (`#next-step`).
    - Work Plan to review: the project Plans tab at the plan (`?tab=plans#work-plan-<id>`); Work Item recovery,
      replacement and attention: the Plans tab at the Work Item (`#work-item-<id>`) when the item names one.
    - SDD batch: the project Repository tab; connection-test cleanup: the project Connections tab.
  - AI catalog hold (row context): on the affected row only, quiet text "AI catalog quota is exhausted until <time>"
    or "AI catalog is unavailable" with a link to AI catalogs. A hold is never its own item and never attention.
- Pagination: Load more appends the next page and says how many longest-waiting items are shown; groups fill in as
  more loads.
- `src/lib/features/attention/owed-links.ts` is the single kind-to-URL mapping, including a per-kind project-section
  fallback and the per-kind count nouns other screens reuse.

## 3. States

- **loading**: static skeleton rows and the status text "Loading what needs you…"; no counts or attention marks.
  Filter and Refresh stay available.
- **populated**: groups in consequence order; open an item's primary action, a project, or Load more.
- **partial**: only some kinds have items, or more pages remain; only those groups show, Load more continues.
- **empty**: no counted item is loaded and no page remains: "Nothing needs you" with a quiet "Review PR runs" link to
  `UX-pipeline-runs`; under a project filter, "Nothing needs you in this project" with Show all projects. Failed PR
  runs, when present, still follow as the quiet section.
- **error**: a banner with Retry. After a successful load the last items stay and the note says they may have
  changed; on a first load the note says what needs the operator is unknown, and no empty state is shown.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Answer (decision with a run) | `UC-resolve-run-question` 1 | populated, partial | populated | `UX-run-page` | `CAP-PR-operator-decisions` | The run page opens at its Decisions section with the pending question or request. |
| Answer (decision without a run) | `UC-resolve-run-question` 1 | populated, partial | populated | `UX-decision-inbox` | `CAP-PR-operator-decisions` | The decision worklist opens; Review opens the exact owner subject. |
| Resume run (held PR run) | `UC-deliver-pull-request` *c | populated, partial | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run page opens with its state-driven primary action, such as Resume. |
| Inspect run (failed PR run) | `UC-deliver-pull-request` *d | populated, partial | populated | `UX-run-page` | `CAP-PR-pull-request-delivery` | The run page opens at Next step, naming the owning Work Item recovery when known. |
| Review plan | `UC-execute-work-plan` 2c | populated, partial | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | The project Plans tab opens at the proposed Work Plan. |
| Inspect Work Item | `UC-execute-work-plan` 4c | populated, partial | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | The Plans tab opens at the Work Item in attention. |
| Inspect recovery | `UC-execute-work-plan` 5c | populated, partial | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | The Plans tab opens at the recovering Work Item. |
| Accept replacement | `UC-execute-work-plan` 6c | populated, partial | populated | `UX-work-plans` | `CAP-WORK-work-plan-execution` | The Plans tab opens at the Work Item whose replacement evidence awaits acceptance. |
| Inspect batch | `UC-execute-sdd-batch` 4c | populated, partial | populated | `UX-sdd-batch` | `CAP-SDD-workflow-control` | The project Repository tab opens; load its retained batches to inspect the batch. A batch deep link is a follow-up (`FB-attention-sdd-batch-deep-link`). |
| Review cleanup | `UC-verify-project-connection` 7 | populated, partial | populated | `UX-connection-tests` | `CAP-CONN-connection-verification` | The project Connections tab opens with the cleanup review. |
| Open project | global: inspect the item's owning project | populated, partial | populated | `UX-project-detail` |  | The project detail opens. |
| Open AI catalogs (hold context) | global: inspect the catalog that holds a run | populated, partial | populated | `UX-ai-catalogs` |  | AI catalog configuration opens. |
| Choose a project | global: narrow triage without deciding | populated, partial, empty, error | loading |  | `CAP-PR-owed-items` | The list restarts at its first page for that project and the URL carries `?project=`. |
| Load more | global: browse the owed set | partial | populated, partial |  | `CAP-PR-owed-items` | The next page is appended; a failure keeps loaded rows and shows the error banner. |
| Refresh / Retry | global: recover or update triage | populated, partial, empty, error | loading |  | `CAP-PR-owed-items` | The first page and the shell counts reload; loaded rows stay until the response replaces them. |
| Review PR runs (empty) | global: quiet overview when nothing is owed | empty | populated | `UX-pipeline-runs` |  | The PR run list opens. |
| Show all projects (filtered empty) | global: leave the project filter | empty | loading |  |  | The landing reloads for all projects. |

## 5. Evidence

Implementation inspected: `modules/hub-ui/src/routes/+page.svelte`,
`modules/hub-ui/src/lib/features/attention/AttentionView.svelte`, `OwedGroupSection.svelte`, `OwedRow.svelte`,
`attention.svelte.ts`, `owed-kinds.ts`, `owed-links.ts` and `owed-counts.svelte.ts`. Checks: `AttentionView.integration.test.ts`
covers group order with failed runs last and quiet, every kind's row (cause, subject, project link, waiting age and its
single action target), the catalog hold on the affected row only, the inbox fallback for a decision without a run,
partial kinds, empty, failed-runs-only, loading, error with retained data and first-load error, Load more with cursor
and limit 100, the project filter and its URL, the `?project=` initial filter with one read, one single-flight counts
read on mount sizing a partial list, loaded-row counts once every page is loaded, and the summary hidden in the empty
state; `AttentionLoadMore.integration.test.ts` covers Refresh and a project change during Load more, after which Load
more works and issues its request; `owed-links.test.ts` covers every kind's link, the project-section fallback and the
count nouns; `owed-kinds.test.ts` covers order, grouping, waiting age and hold text. Mocked-API screenshots (light,
dark, 390px; populated, empty, error) were reviewed during development; no live deployment was exercised.
