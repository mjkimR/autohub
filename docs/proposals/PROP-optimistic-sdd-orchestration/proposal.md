---
id: PROP-optimistic-sdd-orchestration
title: Delegate SDD execution to repositories and agents
summary: "Remove Hub-side SDD runtime preparation and workflow evaluation. Start repository work optimistically through ordinary PR delivery and observe repository-owned GitHub Actions checks."
status: reviewing
created_at: 2026-11-13
target_area: capabilities/sdd/
priority: high
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
    - modules/hub/app/features/project_management/
    - modules/hub/app/features/execution/flows/
    - modules/hub/app/features/execution/tasks/domains/maintenance/
    - modules/hub/app/mcp/
    - modules/hub/migrations/
    - modules/hub/tests/
    - modules/hub-ui/src/
    - packages/sdk/
    - config/
    - scripts/
    - docker/
    - .github/workflows/
    - justfile
    - docs/
    - README.md
  excludes:
    - .devkit/managed/
    - .agents/skills/
    - .codex/
    - .devkit/config.toml
    - pyproject.toml
    - uv.lock
task_kind: feature
workflow: sdd-proposal
---

# [PROP-optimistic-sdd-orchestration] Delegate SDD execution to repositories and agents

## 1. Background & Hypothesis

Hub prepares a repository-specific devkit runtime, restores its managed assets,
evaluates its workflow and dispatches one stage at a time. This makes repository
setup and correctness prerequisites of Hub orchestration. The intended boundary
assigns those responsibilities to the repository and its working agent.

Hub should start requested work optimistically and retain its existing PR owner,
operator questions, delivery identity, retries and GitHub CI/merge observation.
Hub-side `devkit sync` is removed without a replacement runner or Actions job.
Repository verification, when configured, executes in repository-owned GitHub
Actions. This does not change Auto Hub's own contributor SDD workflow.

## 2. Technical Spike Questions

- **Q1**: Which evaluator dependencies must disappear together from launch,
  progression, decisions, milestone batches and the SDK bridge?
- **Q2**: Which existing PR/question/CI mechanisms support optimistic execution
  without a new worker result protocol or remote evaluator?
- **Q3**: How are active native runs and claims settled while preserving history
  and preventing accidental redispatch or newly authorized merging?

## 3. Proposed Design & Impact

Keep explicit single-activity launch and ordinary PR delivery. Remove Hub-side
runtime installation, asset restoration, workflow evaluation and repository
eligibility guarantees. Planning will specify the dependent UI/API removals,
legacy-run disposition and executable acceptance checks before Development.

## 4. Lifecycle & Retirement Criteria

Planning produces a preliminary ADR, a concrete removal inventory and a Living
Spec blueprint. Direction acceptance precedes production changes. One feature
spec delivers the boundary change across backend, UI, SDK integration, packaging
and documentation; these are coupled consumers of the same evaluator.
