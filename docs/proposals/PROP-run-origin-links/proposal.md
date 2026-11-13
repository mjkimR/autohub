---
id: PROP-run-origin-links
title: Run origin links on PR runs
summary: Expose where a PR run came from (Work Item, Work Plan, SDD batch, provider session, enrollment source) on the run read so the run page and lists can link back to its origin.
status: draft                         # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: capabilities/delivery/
priority: medium                      # critical | high | medium | low
size: M                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: medium               # low | medium | high (hint for Planning)
dev_effort: medium                    # low | medium | high (hint for Development)
boundaries:
  owns:
    - capabilities/delivery/
    - ux/delivery/
    - modules/hub/app/features/project_management/
    - modules/hub/tests/
    - modules/hub-ui/src/lib/api/
  excludes:
    - docs/decisions/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-run-origin-links] Run origin links on PR runs

## 1. Background & Hypothesis

Split from `SPEC-owed-item-contract` on the user's decision in its Planning: run origin fields serve the run page, not
the owed-item contract, whose subject needs only type, ID and project.

The app-wide UX review of 2026-11-13 (designer increment I5; relationships R4, R11 and R19) found that a PR run has no
path back to where it came from. `PipelineRun` and `PipelineRunRead`
(`modules/hub/app/features/project_management/pipeline_runs/schemas.py`) carry no Work Item, Work Plan, SDD batch,
provider session or enrollment source. Links exist only on the other side: `WorkItem.pipeline_run_id`,
`AICatalogSession.pipeline_run_id` and `SddActivityClaim.run_id`. No enrollment source is persisted. Evidence:
`docs/proposals/PROP-owed-item-contract/materials/owed-state-inventory.md` on the `plan-owed-item-contract` branch.

Hypothesis: exposing origin links on the run read lets `UX-run-page` and run rows link back to the Work Item, Work
Plan, SDD batch or provider session, closing the one-way relationships without frontend derivation.

## 2. Technical Spike Questions

- **Q1 (derive or persist)**: Are origin links derived at read time from the existing reverse links, or persisted on
  the run? Is an enrollment source (manual enrollment, Work Plan, native SDD, SDK) recoverable for existing runs?
- **Q2 (read cost)**: How do origin joins stay within the shared connection budget on run list pages?
- **Q3 (consumers)**: Which UI surfaces land with the fields (`UX-run-page`, run rows), and which follow?

## 3. Proposed Design & Impact

Direction, to be settled in Planning: add origin fields to the run read (Work Item and Work Plan IDs, SDD batch ID,
provider session ID, enrollment source), with deep-link-ready IDs and the project. Expected impact: the delivery
capability's run read contract, `UX-run-page`, typed client regeneration, and possibly a migration if Q1 persists an
enrollment source.

Non-goals:

1. The per-run pending-decision flag, which `SPEC-owed-item-contract` delivers.
2. Changing how runs are enrolled or linked.

## 4. Lifecycle & Retirement Criteria
<!--
- Preliminary decisions: devkit spec proposal padr run-origin-links "<title>" --summary "<Y-statement: For <context>, we <decision>, to <quality>, accepting <downside>.>" records a PADR in decisions/.
- Research: collect benchmarks and references in materials/ (created with its first file).
- On acceptance (plan-accept): devkit spec proposal accept run-origin-links --by user records gate:plan-accept and status:
  accepted, then the Planning branch is merged; an eligible draft may instead be accepted with --direct on the base,
  without Planning. Development starts with devkit spec proposal handoff run-origin-links.
- On rejection: change only status: rejected, with the user's decision and reason as a decision sentence in the
  commit message (no quote); a later hygiene pass writes the rejection ADR and deletes the proposal directory.
-->
