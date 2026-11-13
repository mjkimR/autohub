---
id: CAP-SDD-native-delivery
title: Repository-owned SDD activity delivery
summary: "Start explicit repository-owned SDD activity intent through ordinary PR delivery. Exact project-scoped retained batch addresses remain read-only history independently of current unit selection."
area: sdd
status: active
usecases:
  - UC-start-sdd-activity
  - UC-complete-sdd-workflow
  - UC-decide-sdd-proposal
  - UC-preview-sdd-milestone
  - UC-execute-sdd-batch
entrypoints:
  - modules/hub/app/features/project_management/sdd/api.py
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/activity_claims.py
---

# [CAP-SDD-native-delivery] Repository-owned SDD activity delivery

## 1. Summary

An operator requests Planning or Development for an exact repository unit. Hub
creates its activity branch and Draft PR, then uses the ordinary PR owner.
`ADR-repository-owned-sdd-execution` records the responsibility decision.
`UC-start-sdd-activity` ends at registration; `UC-complete-sdd-workflow` follows
its work, questions and GitHub outcome.

## 2. Scope & Boundary

- **In-Scope**: explicit activity intent, GitHub branch/PR publication, exclusive
  recoverable claims, descriptive unit context and retained native history.
- **Out-of-Scope**: repository setup, generated assets, devkit policy, workflow
  interpretation, prerequisites and correctness belong to the repository and its
  working agent. `CAP-PR-pull-request-delivery` owns attempts, CI and merge;
  `CAP-PR-operator-decisions` owns questions and explicit answer application.
- **Scope Excluded**: embedded or remote evaluator, a `devkit sync` service,
  executable milestone readiness, graph-derived batches and replacement queues.

## 3. Business Rules & Policies

1. **Optimistic dispatch**: WHEN an authorized operator requests an activity, Hub MUST treat its unit/activity as work intent without proving SDD readiness. Check: `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py` and unit `sdd/test_activities.py`.
2. **Repository responsibility**: Hub MUST leave repository setup, asset management and workflow interpretation to the repository and its working agent. Check: `modules/hub/app/features/project_management/sdd/activities.py`; review of implementation instructions.
3. **No sync delegation**: Hub MUST NOT run or delegate `devkit sync` as an activity prerequisite or replacement service. Check: source/import and serving-image inspection.
4. **Host admission**: WHEN starting work, Hub MUST validate project access, enabled connection/catalog, input shape, GitHub refs and exclusive activity/PR ownership. Check: activity ownership tests under `modules/hub/tests/integration/features/project_management/sdd/`.
5. **No repository eligibility gate**: Hub MUST NOT refuse activity intent because of proposal status/size, devkit adoption, dependencies, receipt, lock, Python range or bundle availability. Check: `modules/hub/tests/unit/features/project_management/sdd/test_activities.py`.
6. **Draft publication**: WHEN publishing either activity kind, Hub MUST create a Draft PR without a server-authored proposal-state commit. Check: `modules/hub/app/features/project_management/sdd/activities.py` and its activity tests.
7. **Exact recovery**: WHEN publication has an uncertain result, Hub MUST preserve the original request, claim and exact saved branch/PR artifacts for reconciliation. Check: activity claim/recovery tests under `modules/hub/tests/integration/features/project_management/sdd/`.
8. **Merge boundary**: WHILE an activity PR is Draft, Hub MUST withhold merge under the ordinary PR contract. Check: `modules/hub/tests/integration/features/project_management/pipeline_runs/test_merge_stage.py`.
9. **Retired surfaces**: Hub MUST refuse live native workflow evaluation, milestone execution preview, batch creation/resume and native typed decision mutations with `SDD_EXECUTION_RETIRED` where their tombstone route is retained. Check: `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.
10. **Historical reads**: WHEN retained native runs, decisions, batches or claims are read, Hub MUST return their stored evidence without restoring an evaluator or granting execution authority. Check: history API tests under `modules/hub/tests/integration/features/project_management/sdd/`.
11. **Uncertain reservation**: WHILE a retired claim or an unleased uncertain publication without a Run retains external ownership, Hub MUST require explicit project-scoped reconciliation before releasing that reservation. Check: `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.
12. **No implicit conversion**: Hub MUST NOT convert a legacy native Run into an optimistic Run through generic resume. Check: `modules/hub/app/features/project_management/sdd/execution.py` and retirement migration tests.

13. **Exact retained batch**: WHEN a Repository address names a batch, Hub MUST load its exact project-scoped detail without requiring membership in the latest-fifty list. Missing subjects never select another batch. Check: `test_origins.py`, `sdd-batches.integration.test.ts` and `RepositoryView.integration.test.ts`.

## 4. Interfaces & Data Contracts

All paths are under `/api/v1/projects/{project_id}/sdd` and require the existing
application authorization boundary.

| Interface | Contract |
| --- | --- |
| `GET /proposals` | Descriptive proposal metadata and activity/run links on an explicit base; metadata is no eligibility proof |
| `POST /proposals/{slug}/planning` | Explicit Planning intent with client request UUID, base, optional effort/catalog |
| `POST /proposals/{slug}/development` | Explicit Development intent with the same publication/recovery contract |
| `GET /runs?spec_dir=...` | Retained unit-bound Run history |
| `GET /batches`, `GET /batches/{batch_id}` | Retained batch selection, member and claim evidence |
| `GET /claims/{claim_id}` | Exact retained claim and checkpoint digest |
| `POST /claims/{claim_id}/reconcile` | `request_id`, `expected_checkpoint_digest`, `acknowledge_external_work: true`; releases the selected retired reservation or eligible unleased uncertain no-Run publication; acknowledges an exact linked terminal retired Run |
| `POST /runs/{run_id}/reconcile` | `request_id`, `expected_revision`, `acknowledge_external_work: true`; acknowledges a terminal retired Run's external work without changing its state |

Optimistic `sdd_snapshot` records `execution_version: 2`,
`provider: repository-agent`, `spec_dir`, requested activity/handoff intent and
optional effort. It is descriptive context, not a workflow/runtime contract.
Legacy snapshots lack that version and remain inspect-only. Both activity kinds
use `plan-<slug>` or `dev-<slug>` and the same ordinary PR owner. GitHub API
publication makes an unchanged-tree intent commit so the Draft PR has an exact
activity candidate; it does not edit proposal content or status.

A start retry reuses its UUID and identical payload. An unrelated branch or
active owner remains a conflict. Unknown remote effects are retained, not treated
as absent or rolled back. A current optimistic claim is releasable only when its publication is uncertain,
no Run is bound and no live lease remains. Release preserves its saved artifacts
and does not adopt/delete a remote branch; an existing branch remains a conflict
for a distinct start. Active owners must be followed or settled through their Run. A retired Run
acknowledgment alone does not release an independently retained unsettled claim;
new enrollment checks both holds.

Repository `batch=<UUID>` addresses restore exact retained detail independently of the selected unit.
The client merges addressed detail into retained options; Load retained batches fetches the list once per project/mount and preserves detail selection.
Refresh status deliberately reloads selected detail. Detail and list failures remain separate; older address/project responses cannot replace the current subject.
Opening, changing or reloading history sends no create, resume or control request.

Legacy local Stop can settle future batch admission;
it neither resumes admitted work nor cancels external agent work.

## 5. Source and Verification Evidence

The activity API, claim owner and ordinary PR lifecycle define this contract.
Tests cited above are enforcing-source pointers; their presence is not a claim
that they were executed or that a live provider/GitHub deployment passed.
`ARCH-06-execution` defines retirement and ownership structure;
`CAP-SDD-workflow-control` and `CAP-SDD-runtime-isolation` retain retired boundary
IDs. `CAP-SDK-existing-pr-bridge` separately owns built-in bridge retirement.
