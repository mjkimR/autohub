---
id: CAP-SDD-native-delivery
title: Native SDD activity and proposal delivery
summary: "Auto Hub starts native proposal activities and previews milestone readiness at a pinned commit. Ephemeral preview selection creates no execution artifacts; existing PR owners retain execution and merge authority. Pending decisions can be discovered through the shared owner-preserving inbox."
area: sdd
status: active
usecases:
  - UC-start-sdd-activity
  - UC-decide-sdd-proposal
  - UC-preview-sdd-milestone
entrypoints:
  - modules/hub/app/features/project_management/sdd/api.py
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/plan_publication.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
---

# [CAP-SDD-native-delivery] Native SDD activity and proposal delivery

## 1. Summary

Native SDD connects devkit proposal/spec workflows to durable `PipelineRun`
execution. Hub creates activity branches and PRs, inspects workflow evidence and
publishes operator or delegated proposal decisions. The existing PR owner retains
CI observation and merge control.

## 2. Scope & Boundary

- **In-Scope**: activity start admission, proposal/spec binding, proposal decision
  publication, decision recovery, proposal approval fences and observational milestone preview.
- **Out-of-Scope**: `CAP-SDD-runtime-isolation` owns isolated evaluation and
  restore; `CAP-SDD-workflow-control` owns native stage answers, holds and
  integration authority. Devkit owns workflow definitions/document authoring;
  providers own implementation; GitHub owns CI. Work Plan admission, milestone
  batch execution and adoption of SDD for Auto Hub's own development are excluded.
- **Scope Excluded**: generic resume as approval, cross-proposal branch acceptance,
  repository evidence as independent merge authority, and retrospective approvals.

## 3. Business Rules & Policies

1. **Start admission**: WHEN an activity start is requested, Hub MUST require an
   enabled `sdd` project with a GitHub repository and connector before creating
   activity artifacts. Source: [usecases.py](../../../modules/hub/app/features/project_management/sdd/usecases.py).
2. **Inactive lifecycle**: IF the evaluated base development approach is
   `adaptive-dev`, THEN Hub MUST refuse Planning/Development with HTTP 409 and
   `SDD_LIFECYCLE_INACTIVE` before creating a branch or PR.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_adaptive_dev_base_refuses_starts_before_creating_branches`.
3. **Planning eligibility**: WHEN a new Planning branch is needed, Hub MUST require a draft
   proposal with no decomposition requirement, size S/M/L or absent, and plan-intent
   satisfied by devkit's base evaluation before starting its branch.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_start_refuses_a_proposal_in_the_wrong_state`, `test_planning_starts_for_every_size_the_gate_allows`, `test_planning_refusal_reports_what_the_base_evaluation_found`.
4. **Planning artifacts**: WHEN an eligible Planning start has no existing activity
   branch, Hub MUST create `plan-<slug>` with the proposal changed to `reviewing`
   and a ready PR bound to the proposal run.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_planning_starts_plan_branch_with_reviewing_and_a_ready_pull_request`.
5. **Development artifacts**: WHEN Development is requested for an accepted
   proposal with no existing activity branch, Hub MUST create `dev-<slug>` with an
   empty start commit and a draft PR enrolled for handoff-first execution.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_development_starts_dev_branch_with_a_handoff_first_run`.
6. **Existing branch ownership**: IF an activity branch already exists, THEN Hub
   MUST reuse its own marker-bearing open PR or refuse the start with HTTP 409 / `SDD_BRANCH_EXISTS`
   rather than overwrite an unrelated branch.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_existing_branch_refuses_unless_it_carries_hubs_own_pull_request`.
7. **Effort selection**: WHEN enrolling an activity, Hub MUST use an explicit
   `activity_effort` before the proposal's activity-specific effort hint.
   Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_activity_effort_uses_the_proposal_hint_unless_overridden`.
8. **Evaluation ownership**: WHEN an activity or proposal operation needs repository
   evaluation, Hub MUST delegate it to `CAP-SDD-runtime-isolation` rather than
   install or select tooling from the target request.
   Check: [test_profiles.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_profiles.py).
9. **Readiness is observational**: WHEN readiness or related executions are read,
   Hub MUST leave execution unstarted and Git unchanged.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_native_enrollment_requires_spec_and_readiness_is_read_only`, `test_spec_runs_are_exact_project_scoped_and_do_not_advance`.
10. **Decision basis**: WHEN a proposal decision is submitted, Hub MUST fence it
    against its request identity, actor, inspected PR head, run/project revisions,
    current binding and workflow evidence before publication.
    Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_proposal_acceptance_is_committed_by_hub_and_merged_by_policy`; [test_plan_authorization.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_authorization.py), `test_a_question_arriving_during_preparation_fences_the_push`.
11. **Acceptance gate**: WHEN accepting a proposal manually, Hub MUST require its
    own Planning branch and an unheld, reviewing proposal waiting for plan-accept.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_acceptance_refuses_another_proposals_branch_without_publishing`; [test_plan_authorization.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_authorization.py), `test_unapplied_hub_question_blocks_a_proposal_decision`.
12. **Rejection result**: WHEN rejecting a reviewing proposal with nonblank
    feedback, Hub MUST publish its rejected status.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_rejection_changes_status_only_and_closes_open_questions`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_proposal_rejection_needs_a_reason_and_merges_the_status_change`.
13. **Durable publication**: WHEN publishing a decision, Hub MUST persist the exact
    candidate before its bounded push under Run/Project row locks and a confirmed
    head lease.
    Check: [test_plan_publication.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py), `test_stop_before_publication_prevents_external_write`, `test_cancellation_waits_for_a_publication_that_already_holds_the_fence`.
14. **Lost-result recovery**: IF publication has an uncertain result, THEN Hub MUST
    reconcile the exact saved candidate and its authority applicability before
    attempting another publication.
    Check: [test_plan_publication.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py), `test_lost_database_result_recovers_exact_pushed_commit_without_publishing_again`, `test_failed_push_retries_the_same_request_without_losing_audit`.
15. **Delegation ownership**: WHERE automatic plan acceptance is enabled, Hub MUST
    require delegation from both the owning base and proposal policy without
    restoring explicitly withdrawn approval during inspection or generic resume.
    Check: [test_plan_publication.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py), `test_auto_plan_acceptance_requires_owning_base_and_records_policy_authority`, `test_withdrawn_proposal_approval_is_not_restored_by_inspection`; [test_plan_authorization.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_authorization.py), `test_auto_delegation_stays_withdrawn_until_explicit_reapproval`.
16. **Decision commit CI**: WHEN a published decision remains applicable to its
    run, Hub MUST return that run to `awaiting_ci` for the decision commit before
    policy-controlled merge.
    Check: [test_plan_authorization.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_authorization.py), `test_published_decision_head_waits_for_its_own_ci_before_merging`, `test_a_different_head_is_never_allowed_by_the_decision_receipt`.
17. **Handoff lineage**: WHEN handoff-first Development creates a spec, Hub MUST
    continue the bound workflow on that spec with its recorded proposal origin.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_handoff_first_run_follows_the_new_spec_after_the_handoff`; [test_lineage.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_lineage.py).

18. **Development eligibility**: IF a new Development activity's base proposal
    is not accepted, THEN Hub MUST refuse with HTTP 409 / `CONFLICT` before
    creating its activity branch.
    Check: [test_activities.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_activities.py), `test_start_refuses_a_proposal_in_the_wrong_state`.
19. **Rejection question closure**: WHEN rejecting a reviewing proposal with open
    worker questions, Hub MUST close those questions with the rejection decision
    before publishing it.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_rejection_changes_status_only_and_closes_open_questions`.
20. **Inapplicable publication recovery**: IF the remote head matches a saved
    decision candidate but its authority is no longer applicable, THEN Hub MUST
    record that publication with `applied: false` without changing the run state
    or granting approval.
    Check: [test_plan_publication.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py), `test_lost_database_result_recovers_exact_pushed_commit_without_publishing_again`.

21. **Pinned preview**: WHEN a milestone preview is requested, Hub MUST resolve its repository ref once and use that full SHA for all membership and prerequisite document reads. Check: `modules/hub/tests/integration/features/project_management/sdd/test_milestone_cli.py`, two-branch/moving-ref fixture.
22. **Direct membership**: WHEN discovering milestone work, Hub MUST use devkit's global/registered-package catalog and exact resolver for direct proposal anchors, including supported historical flat anchors, without adding historical SPEC milestone metadata as members. Check: `modules/hub/tests/integration/features/project_management/sdd/test_milestone_cli.py`.
23. **Separate readiness facets**: WHEN evaluating supported draft or accepted members, Hub MUST expose shared native admission separately from preview dependency scheduling and workflow worker holds. Check: `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py`, admission parity and blocked/question/malformed worker fixtures.
24. **Exact scheduling**: WHEN evaluating a prerequisite, Hub MUST satisfy it only through a done/dropped milestone or an exact canonical completed SPEC, without reopening completed SPEC history or inferring proposal-to-spec lineage. Check: `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py` and real isolated alias fixtures.
25. **Incomplete evidence**: IF the observed graph has missing/ambiguous/nonanchor relations, active cycles, unavailable evidence or an exceeded read bound, THEN Hub MUST report an incomplete preview that permits no selectable order. Check: `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py`, graph/boundary/pagination/runtime fixtures.
26. **Observational preview**: WHEN previewing or selecting milestone work, Hub MUST create no activity, PR, run, decision, repository edit or scheduler queue. Check: `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py`, `modules/hub/tests/integration/features/project_management/sdd/test_milestone_api.py` and UI preview tests.
27. **Existing activities**: WHEN a matching branch exists, Hub MUST expose its marker-bearing owned PR and optional exact project-scoped run as inspect-only evidence, or an unrelated-branch hold. Check: `modules/hub/tests/unit/features/project_management/sdd/test_milestones.py`, owned-PR-before-enrollment and pagination fixtures.
28. **Ephemeral subset**: WHEN an operator selects milestone activities, Hub MUST retain only explicitly selected eligible direct members of a complete preview in deterministic canonical-ID topological order. Check: `modules/hub-ui/src/lib/features/project-management/repositories/milestone-selection.test.ts` and `SddMilestonePreview.integration.test.ts` beside it.
29. **Context invalidation**: WHEN project, ref, milestone or explicit refresh changes, Hub MUST clear local selection and discard obsolete preview responses. Check: `modules/hub-ui/src/lib/features/project-management/repositories/SddMilestonePreview.integration.test.ts`.

### Proposal discovery

WHEN a persisted native proposal is actionable, Hub MUST expose its exact proposal decision identity in the shared worklist without creating a second mutation owner. In-progress/published proposal decisions are excluded. Discovery does not accept, publish, hand off or merge work. `CAP-SDD-workflow-control` owns exact-subject inspection and native generation guards; `CAP-PR-operator-decisions` owns the shared listing interface. Check: [discovery.py](../../../modules/hub/app/features/project_management/sdd/discovery.py), reviewed against the existing owner predicates.

`UC-decide-sdd-proposal` enters through `UX-decision-inbox` or the existing run surfaces; proposal decisions retain their existing publication and authority guards.

### Decision recovery outcomes

WHEN a proposal publication is prepared or uncertain, Hub MUST disclose retained candidate commit identities through the exact owner outcome read defined by `CAP-PR-operator-decisions`. Several candidates do not imply one authoritative publication. Check: `test_prepared_candidates_and_legacy_context_stay_truthful` in [test_outcomes.py](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_outcomes.py).

WHEN the operator reviews publication reconciliation, the interface MUST explain its inspection/possible continuation effect and use a separate stable recovery intent against refreshed current Run context. It preserves the original uncertain proposal intent. An unresolved recovery request blocks competing original submissions and retries, while its own exact retry remains available. Ended Runs offer no recovery continuation. Check: [RunDecisionsDialog.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/RunDecisionsDialog.integration.test.ts) and [decision-intents.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/decision-intents.integration.test.ts).

## 4. Interfaces & Data Contracts

All endpoint paths below include the `/api/v1` mount.

| Interface | Request / result |
| --- | --- |
| `GET /api/v1/projects/{project_id}/sdd/milestones` | Required `ref`; captured SHA, complete flag/reasons and global/package active/archive catalog for the Hub selector |
| `POST /api/v1/projects/{project_id}/sdd/milestone-preview` | Required `ref`, `milestone_id`; optional exact `milestone_path`; `MilestonePreview` observation |
| `GET /api/v1/projects/{project_id}/sdd/proposals` | `base_branch` defaults to `main`; returns base identity, proposal actions, activity PRs, related waiting run and `truncated` |
| `POST /api/v1/projects/{project_id}/sdd/proposals/{slug}/planning` | `StartActivityRequest`; HTTP 201 `PipelineRunRead` |
| `POST /api/v1/projects/{project_id}/sdd/proposals/{slug}/development` | `StartActivityRequest`; HTTP 201 `PipelineRunRead` |
| `GET /api/v1/projects/{project_id}/sdd/runtime` | Runtime profile, bundle inventory, lock/revision identity and isolation result |
| `POST /api/v1/projects/{project_id}/sdd/readiness` | `pull_number`, `spec_dir`; result includes `ready`, reason, head/base, CLI/workflow/current evidence and warnings |
| `POST /api/v1/pipeline-runs/{run_id}/resume` | Proposal decisions use `request_id`, `expected_revision`, `decision`, `head_sha`, optional `feedback` |
| `GET /api/v1/pipeline-runs/{run_id}/sdd-decisions` | Durable decision evidence, including candidate/publication outcome |

`MilestonePreview` carries project/repository identity, requested ref and resolved SHA, exact milestone identity/path/status, repository observation time, runtime identity, completeness/reasons, counts/limits, prerequisite nodes/edges and member rows. Rows distinguish `eligible_now`, `held`, `existing_activity`, `finished`, `unsupported` and `unknown`. Admission and scheduling are separate facets; workflow holds retain exact worker evidence. Valid flat or package proposal anchors unsupported by native start remain inspect-only. Reviewing/rejected proposals offer no new activity.

Preview bounds are 50 direct members, 200 distinct prerequisite anchors, 500 dependency edges and a 150-second request deadline. Evaluation is sequential in one pinned checkout with one runtime restoration. Matching activity PR observation allows 10 pages of 100 rows; an exhausted full tenth page or failed later page is incomplete. Counts are observed coverage, not an estimate of unseen work. Incomplete previews expose no selected order. Done/dropped milestones remain inspectable without executable selection.

A milestone prerequisite accepts only an MS identity. A work prerequisite accepts only an exact PROP/SPEC anchor. Draft, reviewing, accepted and rejected PROP prerequisites remain held; origin metadata and matching slugs supply no canonical mapping. Only the devkit resolver's unambiguous canonical result supplies one. The pinned runtime's supported aliases retain their own document prefix. An unfinished member is not released by selecting another member first.

Run/PR observations carry their own timestamp and exact known head/base IDs. An owned PR remains inspectable before any run exists; no run is fabricated. External observations are not atomic with the repository snapshot. The response carries no execution authority token. Later activity start evaluates its existing admission afresh; preview scheduling adds no start gate.

Existing project access and enabled-SDD/connection checks precede evaluation. Invalid paths, unknown/ambiguous milestones and path/ID mismatches refuse with HTTP 422; an unreadable member/runtime/dependency yields incomplete evidence. The request never falls back to main.

`StartActivityRequest` requires UUID `request_id`; `base_branch` defaults to
`main`; optional `activity_effort` is `low`, `medium` or `high`; optional `catalog`
selects admission. Slugs match `[a-z0-9][a-z0-9_-]*` with at most 59 characters.
The bound `spec_dir` names `docs/proposals/PROP-<slug>` or
`specs/YYYY-MM/<unit>`; its anchor is `proposal.md` or `spec.md` respectively.

Proposal decisions are `accept_plan` or `reject_plan`. They require a 40-character
lowercase hexadecimal `head_sha` and a current `expected_revision`; rejection
requires nonblank `feedback`. They cannot be combined with `workflow_answer` or
`answer_id`. `gate:plan-accept` cannot be answered as a generic workflow answer.
Published commits preserve actor/reason evidence; their author comes from
`AUTOHUB_SDD_COMMIT_IDENTITY`, default `AutoHub <autohub@users.noreply.github.com>`.

HTTP 409 uses `CONFLICT` by default; inactive lifecycle uses
`SDD_LIFECYCLE_INACTIVE`; concurrent decision preparation uses
`SDD_DECISION_IN_PROGRESS`; an unrelated activity branch uses `SDD_BRANCH_EXISTS`. Invalid requests use HTTP 422 / `INVALID_REQUEST`;
invalid configured commit identity uses `SDD_IDENTITY_INVALID`. A runner failure
can leave remote activity artifacts or uncertain publication evidence: no automatic
rollback or renewed approval is implied.

## 5. Source and Verification Boundary

Interfaces derive from [sdd/api.py](../../../modules/hub/app/features/project_management/sdd/api.py),
[sdd/schemas.py](../../../modules/hub/app/features/project_management/sdd/schemas.py),
[interaction_schemas.py](../../../modules/hub/app/features/project_management/pipeline_runs/interaction_schemas.py),
[activities.py](../../../modules/hub/app/features/project_management/sdd/activities.py),
[plan_decisions.py](../../../modules/hub/app/features/project_management/sdd/plan_decisions.py)
and [plan_publication.py](../../../modules/hub/app/features/project_management/sdd/plan_publication.py).
The linked checks identify source-level regression evidence, not a claim that all
suites were executed while writing this contract. Runtime provisioning and operator
procedures remain in the [runtime operations guide](../../operations/sdd-runtime.md).
`CAP-SDD-runtime-isolation` defines receipt/restore/drift/isolation guarantees;
`CAP-SDD-workflow-control` defines native workflow continuation and integration authority.
