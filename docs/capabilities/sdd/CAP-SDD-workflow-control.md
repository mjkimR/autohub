---
id: CAP-SDD-workflow-control
title: Retired native SDD workflow authority
summary: "Hub-native workflow stage evaluation and typed SDD decisions are retired. Stored decisions remain inspectable, while new activities use ordinary PR questions, explicit resume and GitHub merge policy."
area: sdd
status: deprecated
usecases:
  - UC-decide-sdd-proposal
entrypoints:
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
  - modules/hub/app/features/project_management/pipeline_runs/usecases/control.py
---

# [CAP-SDD-workflow-control] Retired native SDD workflow authority

## 1. Summary

Hub does not select devkit stages, interpret envelopes or author repository
acceptance, handoff, answer, return or integration records.
`ADR-repository-owned-sdd-execution` assigns internal repository workflow to its
working agent. `CAP-PR-operator-decisions` owns new Run questions;
`CAP-PR-pull-request-delivery` owns current-head CI and merge.

## 2. Scope & Boundary

- **In-Scope**: retained native decision history and permanent refusal of old
  execution authority.
- **Out-of-Scope**: live repository policy and workflow belong to the repository
  and agent. `CAP-SDD-native-delivery` owns descriptive activity context and
  legacy claim reconciliation.
- **Scope Excluded**: Hub-native proposal acceptance/rejection, stage dispatch,
  workflow answers, approval publication and runtime/evidence reevaluation.

## 3. Business Rules & Policies

1. **Retired authority**: WHEN a caller attempts native workflow control or resumes an old native Run, Hub MUST refuse with `SDD_EXECUTION_RETIRED` before remote effects. Check: native retirement API/progression tests.
2. **Historical decisions**: WHEN retained decisions are read, Hub MUST return stored receipts without updating repository state or restoring their former authority. Check: native history API tests.
3. **Ordinary input**: WHEN a new optimistic activity needs operator input, Hub MUST use the existing Run question/answer and explicit-resume contract. Check: `modules/hub/app/features/project_management/pipeline_runs/interaction_service.py` and ordinary interaction tests.

## 4. Interfaces & Data Contracts

Old `sdd_snapshot` and `sdd_progress` values remain historical data. Their stage,
request, approval, report and publication fields are not a live decision source.
New snapshots with `execution_version: 2` carry activity intent only.

Native decision history stays read-only. Saving a generic answer does not resume
work, satisfy a repository gate or mark a PR ready. A Draft PR remains the
operator's merge boundary under `CAP-PR-pull-request-delivery`.

## 5. Verification Boundary

The retired-execution discriminator, generic interaction paths and retained
receipt reads define this boundary. Source/test inspection is separate from
executed checks and live deployment evidence.
