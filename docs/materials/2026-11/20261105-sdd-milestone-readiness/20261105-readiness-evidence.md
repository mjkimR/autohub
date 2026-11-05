---
id: MAT-sdd-milestone-readiness
title: Milestone preview source evidence
summary: "Source inspection for milestone membership, native admission reuse and bounded preview design."
created_at: 2026-11-05
---

# [MAT-sdd-milestone-readiness] Milestone preview source evidence

Inspected at `bd2fa21db684e09e9245cbeb2d132f5dd40ade05`. This is code/test inspection, not test execution or deployment evidence.

- `.devkit/managed/spec/skills/spec/references/roadmap-catalog.md:14-17`: only direct PROP membership; PROP/SPEC unit dependencies; MS-only milestone dependencies; no spec milestone inheritance.
- `.devkit/managed/spec/skills/spec/references/backlog.md:69-74`: registered package/global roadmap roots and same-root archives; aliases remain repository-wide.
- `modules/hub-ui/src/lib/features/project-management/repositories/Roadmap.integration.test.ts:6-11`: four root/archive cases; selected branch callback opens proposal anchors.
- `modules/hub/app/features/project_management/sdd/activities.py:132-168`: draft/decomposition/size and accepted-proposal checks before shared `start_blocker`; existing branch ownership checked first.
- `modules/hub/app/features/project_management/sdd/policy.py:44-70`: workflow evidence and lifecycle evaluation via isolated checkout/restore and server runtime CLI.
- `modules/hub/app/features/project_management/sdd/proposals.py:134-168`: proposal list is capped at 50 and uses a selected base SHA; its display actions are hints rather than runtime admission.
- `modules/hub/app/features/project_management/sdd/repos.py:5-28`: exact project/unit or recorded handoff lineage, latest 20 runs; neither a similarly named spec nor a partial run list proves completed delivery.
- `modules/hub-ui/src/lib/features/project-management/repositories/RepositoryView.svelte:295-311`: Hub panels remain separate from vendor viewer; path callback can prefill a recognized selection without modifying vendor code.

The single panel and dedicated screen are viable arrangements. The panel keeps bounded selection and review in one place. A viewer-only change fails the ownership constraint. Conservative graph limits are product implementation bounds, not a measured throughput promise. No temporary probe was needed.

The Scout was read-only with explicit worktree paths and reported no outside reads/writes. Its early invocation lacked a pre-run temporary-index snapshot; clean status after its return and its no-write declaration are weaker substitute evidence, not a native isolation guarantee. Subsequent support reviews use before/after Git tree snapshots.

## Review fold evidence

- `.devkit/managed/spec/skills/spec-next/references/next-work.md:10-12,30-40`: milestone dependencies pass for done/dropped; direct unit prerequisites require exact completed SPEC at the captured base; completed prerequisites are not reopened; this schedules work and adds no start gate.
- `modules/hub/app/features/project_management/sdd/services.py:69-97` and `progress.py:78-83`: reuse hold projection separately from start eligibility. `planning_blocker` can pass completed intent despite a later hold; Development start checks do not supply all workflow holds.
- Challenger P1/P2 folded: step 6 and MR-04 align scheduling; step 3 and MR-03 separate native admission from preview scheduling/worker holds. Sequential per-unit evaluation avoids assuming concurrent CLI safety or a batch API.
- UX findings folded: Repository viewer owns the milestone selector/Preview action; proposal members remain SDD units. Context changes during loading/held/incomplete/error and refresh from selected clear old selection and invalidate obsolete requests.
- Challenger and UX reviewer both reported no outside reads/writes. Pre/post temporary-index tree `ca6e6fef0ca3d80a667f431901f201650ad544ec` matched. Native confinement is not claimed. Original UX findings remain recorded for Host plan-accept review; the author checked these fixes without a second UX round.
