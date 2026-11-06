---
id: PROP-work-plan-templates
title: Create fresh Work Plans from reusable templates
summary: "Save reusable Work Plan specifications, local dependencies and execution preferences, then create explicitly reviewed new registrations without copying execution history or authority."
status: draft
created_at: 2026-11-06
target_area: capabilities/work-plans/
priority: low
size: M
planning_effort: medium
dev_effort: high
boundaries:
  owns:
  - modules/hub/app/features/project_management/work_plans/
  - modules/hub/migrations/
  - modules/hub/tests/integration/features/project_management/work_plans/
  - modules/hub/tests/integration/migrations/
  - modules/hub-ui/src/lib/api/
  - modules/hub-ui/src/lib/features/project-management/work-plans/
  - docs/capabilities/work-plans/
  - docs/usecases/work-plans/
  - docs/ux/work-plans/
  - docs/steering/
  excludes:
  - docs/operations/
  - .github/
  - packages/sdk/
task_kind: feature
workflow: sdd-proposal
---

# [PROP-work-plan-templates] Create fresh Work Plans from reusable templates

## 1. Background & Hypothesis

`CAP-WORK-work-plan-execution` registers task batches with local Item dependencies and execution preferences. Repeating a similar batch requires composing that specification again. Its execution history, merge evidence and replacement relationships belong to a particular registration and cannot serve as a reusable definition.

Save reusable Work Plan definitions and create fresh explicitly reviewed registrations from them. The hypothesis is that repeated maintenance or feature routines can reuse their structure while each execution retains independent identities and authority.

Recommended delivery order: third, after `PROP-mcp-delivery-tools` and `PROP-decision-notifications`. These are product priorities, not required implementation dependencies. Medium size is provisional; Planning should keep the feature to reusable Work Plan definitions and fresh registration.

## 2. Technical Spike Questions

- **Q1**: Should templates initially be project-scoped, and which specification/preferences fields are portable while repository bindings and cross-Plan dependencies require fresh selection?
- **Q2**: What immutable snapshot or revision should a draft creation preview bind so template edits do not silently change an already reviewed registration?
- **Q3**: How should operators save from an existing Plan, edit/delete a template and distinguish saving a definition from requesting execution?

## 3. Proposed Design & Impact

### Candidate scope

- Save a reusable definition from an explicitly selected existing Work Plan or authored template. Include Item specifications, acceptance text, local dependency structure and supported execution preferences.
- Prefer project-scoped ownership for the initial design. Planning compares alternatives and chooses the minimum useful binding model.
- Offer a template picker, editable creation preview and explicit registration confirmation. Saving, editing or opening a template never requests execution.
- Create fresh Plan/Item identities through ordinary Work Plan registration and current validation. Snapshot the selected template revision/content for that request; response-loss retries keep its request identity and reviewed payload.
- Exclude source run/PR/Issue identities, outcomes, attempts, recovery events, replacement links/acceptances and authorization from the reusable definition. External Plan dependencies, schedule dates and repository-specific settings require explicit review instead of silent copying.
- Updating/deleting a template does not mutate Plans already registered from it. Keep template lifecycle separate from execution history and retention.
- Extend `CAP-WORK-work-plan-execution`, `UC-execute-work-plan` and `UX-work-plans`; do not add a second execution scheduler.

### Candidate acceptance examples

- **TEMPLATE-01**: Given a Plan with successful and failed execution history, when its reusable definition is saved, then only supported definition fields and local dependencies are retained; saving starts no work.
- **TEMPLATE-02**: Given a selected template revision, when the operator edits its preview and explicitly registers it, then a fresh Plan with fresh Items uses the reviewed payload and ordinary admission rules.
- **TEMPLATE-03**: Given an existing derived Plan, when its source template changes or is deleted, then that Plan's specification and execution evidence remain unchanged.
- **TEMPLATE-04**: Given a response-lost registration or an invalid dependency/binding, when retried or submitted, then existing idempotency and validation apply without copying prior approval or execution results.

### Non-goals

- **Scope Excluded**: recurring execution schedules, automatic decomposition, cross-project template marketplaces, native SDD templates, SDK flow templates, automatic replacement/recovery and copying original execution authority.
- **Scope Excluded**: Jules integration, production verification, monitoring and CI changes.

## 4. Lifecycle & Retirement Criteria

This is queued feature work with medium Planning and high Development effort. Planning settles template ownership, field portability and snapshot behavior before scope acceptance. The accepted direction hands off through the ordinary lifecycle. Existing Work Plans remain independent of later template edits or deletion.
