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
