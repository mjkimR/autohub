---
id: UX-milestones
title: Open milestones
summary: "An SDD project's Milestones tab lists planned and active milestones on the default branch with their direct proposal members and latest PR runs, and opens a milestone or member in the Repository tab."
area: repository
element: screen
status: active
usecases:
  - UC-inspect-repository-documents
capabilities:
  - CAP-DOC-repository-viewer
---

# [UX-milestones] Open milestones

## 1. Purpose

- **Primary task**: See which milestones are still open and how their proposals are moving, without browsing the repository.
- **Facts to commit**: the default branch read, each open milestone's status and dependencies, and each member's document status and latest PR run per activity.

## 2. Content

The Milestones tab sits in the project's Work group after Plans and appears only for SDD projects. A non-SDD project reached through `?tab=milestones` gets a sentence saying that milestones come from an SDD repository's roadmap.

- Milestone (heading "Open milestones"; a line naming the default branch and that done and dropped milestones stay in the Repository tab's Progress).
- Milestone (one group per milestone at a roadmap root whose status is neither done nor dropped: its title as a link, status badge, the counts of units, units with an active PR run and runs waiting on the operator, and Depends on with each dependency's status).
- Proposal (member row: title as a link, document status badge and unit path).
- PR run (per member, the latest run per activity: activity, PR link, state badge, Draft badge, and Open decisions when the run is paused or blocked).

The note shared with Progress says that statuses neither decide readiness nor order work. Proposals outside milestones and specs are not listed here. The tab starts no work.

## 3. States

- **loading**: "Loading milestones…" while the default branch and roadmap are read; then "Loading PR runs…" until run lines arrive.
- **populated**: open milestone groups in document order.
- **empty**: "No open milestones on this branch" with where planned and active milestones live (`docs/roadmap/`).
- **error**: "Milestone listing incomplete" names the failed reads with Retry milestones. A failed PR run read keeps document statuses and offers Retry PR runs.

## 4. Interactions

| Trigger | Step | From | To | Target | Capability | Feedback |
| --- | --- | --- | --- | --- | --- | --- |
| Open the Milestones tab | `UC-inspect-repository-documents` 1 | loading | populated, empty, error | | `CAP-DOC-repository-viewer` | The default branch roadmap and the project's PR runs are read. |
| Open milestone / member | `UC-inspect-repository-documents` 3 | populated | populated | `UX-repository` | `CAP-DOC-repository-viewer` | The Repository tab opens that document on the default branch with its unit actions. |
| Open PR run / Open decisions | global: follow a member's PR run from its milestone | populated | populated | `UX-run-page` | `CAP-DOC-repository-viewer` | The PR run page opens, at its decisions when the run waits on the operator. |
| Retry milestones | global: reread the default branch roadmap after a failed listing | error | loading | | `CAP-DOC-repository-viewer` | The listing is read again; earlier failures clear. |
| Retry PR runs | global: reload the project's PR runs without discarding document statuses | error | loading | | `CAP-DOC-repository-viewer` | Run lines return when the read succeeds. |

## 5. Evidence

- [MilestonesPanel.svelte](../../../modules/hub-ui/src/lib/features/project-management/repositories/MilestonesPanel.svelte).
- [MilestonesPanel.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/MilestonesPanel.integration.test.ts); test assertions were inspected.
- [progress.ts](../../../modules/hub-ui/src/lib/features/project-management/repositories/documents/progress.ts) `isOpenMilestone`.
- [ProjectDetailView.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/projects/ProjectDetailView.integration.test.ts) covers the tab group and SDD-only tab.

These simulated checks do not establish live repository behavior.
