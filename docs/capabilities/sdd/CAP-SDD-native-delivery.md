---
id: CAP-SDD-native-delivery
aliases: [CAP-SDD-workflow-control, CAP-SDD-runtime-isolation]
title: Repository-owned SDD activity delivery
summary: "Start explicit repository-owned SDD activity intent through prompt, bounded ordinary PR delivery. Durable publication claims preserve exact ownership and uncertain-effect recovery."
area: sdd
status: active
usecases:
  - UC-start-sdd-activity
  - UC-complete-sdd-workflow
entrypoints:
  - modules/hub/app/features/project_management/sdd/api.py
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/activity_claims.py
  - modules/hub/app/features/project_management/sdd/usecases.py
  - modules/hub/app/features/project_management/pipeline_runs/requests.py
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
  recoverable claims and descriptive unit context.
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
9. **Supported interfaces**: Hub MUST expose only repository-owned activity starts, unit Run reads and current claim inspection/reconciliation under the SDD API. Removed evaluation, batch, typed native decision and retired-Run reconciliation routes have no compatibility handlers. Check: `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py` and OpenAPI inspection.
10. **Uncertain reservation**: WHILE an unleased uncertain publication without a Run retains external ownership, Hub MUST require explicit project-scoped reconciliation before releasing that reservation. Check: `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.

11. **Contextual intent**: WHEN a selected proposal requests Planning or Development, Hub MUST submit its reviewed unit/activity/base rather than a stale list selection. Check: `SddProposals.integration.test.ts` selected-unit and context-reset tests.
12. **Explicit PR number**: WHEN enrolling an existing unit PR through the UI, Hub MUST keep submission disabled until the operator supplies a positive integer PR number. Check: `SddExecution.integration.test.ts` blank and fractional-number tests.
13. **Workspace recovery**: WHILE an original request is unresolved, Hub MUST retain its exact recovery controls across document and viewer-mode changes. Check: `SddProposals.integration.test.ts` original-intent recovery; the `sdd-request-recovery` region of `SddStartOutcome.svelte`, mounted by `RepositoryView.svelte` above both viewer modes.
14. **Abandoned claim**: WHEN a start retry finds its claim without a Run, a live lease, a recorded refusal or uncertainty and with a changed project basis, Hub MUST refuse the retry and record the claim as a settled no-effect refusal if no branch or PR write was attempted, otherwise as uncertain for reconciliation under rule 10. Check: `test_crashed_worker_claim_is_released_or_reconcilable_after_project_change` in `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.

15. **Gate question instruction**: WHEN building an SDD activity request, Hub MUST instruct the working agent to raise a stop at a human approval or decision gate of the repository workflow through the attempt-bound question marker after pushing completed work, keeping the marker's attempt and head unchanged, with a decision summary and the expected answers (accept, request changes, reject); never to record or infer the operator's decision before an answer; and to apply a resumed gate answer, including requested changes, as the operator's decision while leaving the PR Draft. The instruction names no repository tool, gate or stage, and Hub neither reads gate state nor refuses Ready status or merge for an unanswered gate. Check: `test_sdd_activity_instructions_raise_repository_gates_as_questions`, `test_ordinary_instructions_have_no_gate_text` and `test_mention_comment_carries_the_gate_instruction_beside_the_question_marker` in `modules/hub/tests/unit/features/project_management/pipeline_runs/test_requests.py`.
16. **Closed refusal**: IF a start is refused with `SDD_BRANCH_EXISTS`, or with any other 4xx status that names no retained claim (`SDD_ACTIVITY_OWNED` or the documented `/sdd/claims/<claim-id>` detail suffix), THEN the UI MUST close that request and keep no start lock for it. Check: `SddUnitPanel.integration.test.ts` start-failure classification and existing-branch refusal tests.
17. **Retained owner request**: IF a 409 or 410 start refusal names a retained claim, THEN the UI MUST keep the exact original request and open that claim's recovery. Check: `SddUnitPanel.integration.test.ts` retained-owner test.
18. **Run-owned request dismissal**: IF the claim of a retained start request is owned by a PR run, THEN the UI MUST offer to close that request, ending its start lock while keeping the link to the owning run. Check: `SddClaimRecovery.integration.test.ts` run-owned dismissal tests; `SddUnitPanel.integration.test.ts` retained-owner test.

## 4. Interfaces & Data Contracts

All paths are under `/api/v1/projects/{project_id}/sdd` and require the existing
application authorization boundary.

| Interface | Contract |
| --- | --- |
| `GET /proposals` | Descriptive proposal metadata and activity/run links on an explicit base; metadata is no eligibility proof |
| `POST /proposals/{slug}/planning` | Explicit Planning intent with client request UUID, base, optional effort/catalog |
| `POST /proposals/{slug}/development` | Explicit Development intent with the same publication/recovery contract |
| Start refusal body | `detail` and, for SDD refusals, `code`: `SDD_BRANCH_EXISTS` (an activity branch with another owner or head) or `SDD_ACTIVITY_OWNED` (a retained activity claim); a refusal raised after the claim exists ends `detail` with `; inspect /api/v1/projects/<project-id>/sdd/claims/<claim-id>` |
| `GET /runs?spec_dir=...` | Retained unit-bound Run history |
| `GET /claims/{claim_id}` | Exact retained claim and checkpoint digest; `DESIGN-sdd-activity-publication` defines the checkpoint fields and digest |
| `POST /claims/{claim_id}/reconcile` | `request_id`, `expected_checkpoint_digest`, `acknowledge_external_work: true`; releases the selected unleased uncertain no-Run publication reservation |

The descriptive `sdd_snapshot` records `provider: repository-agent`, `spec_dir`, requested activity/handoff intent and
optional effort. It is descriptive context, not a workflow/runtime contract. Native progress JSON is absent
from Run storage and API responses; generic resume receipts have no native decision evidence.
Both activity kinds
use `plan-<slug>` or `dev-<slug>` and the same ordinary PR owner. Publication
edits no proposal content or status; `DESIGN-sdd-activity-publication` explains
its intent commit, write order and claim checkpoint.

A start retry reuses its UUID and identical payload. An unrelated branch or
active owner remains a conflict. Unknown remote effects are retained, not treated
as absent or rolled back. A current optimistic claim is releasable only when its publication is uncertain,
no Run is bound and no live lease remains. Release preserves its saved artifacts
and does not adopt/delete a remote branch; an existing branch remains a conflict
for a distinct start. Active owners must be followed or settled through their Run.

## 5. Source and Verification Evidence

The activity API, claim owner and ordinary PR lifecycle define this contract.
Tests cited above are enforcing-source pointers; their presence is not a claim
that they were executed or that a live provider/GitHub deployment passed.
`ARCH-06-execution` defines activity ownership and ordinary PR progression.
`ADR-remove-native-sdd-compatibility` records removal of unused native compatibility.

WHEN an activity claim is durably bound to its Run, Hub MUST attempt ordinary progression for up to 10 seconds without waiting for a scheduler tick. A deferred or failed prompt attempt preserves the successful registration and bound claim; ordinary ticks retain recovery ownership. Project admission, catalog limits and leases still apply. Check: `test_bound_activity_starts_without_another_tick` in `modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.
