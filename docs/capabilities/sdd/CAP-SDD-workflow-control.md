---
id: CAP-SDD-workflow-control
title: Native SDD workflow control and integration authority
summary: "Control native SDD workflow decisions, worker questions and integration authority. Cross-project discovery opens exact subjects through persisted inspection CAS while preserving holds, revocation and publication evidence."
area: sdd
status: active
usecases:
  - UC-execute-sdd-batch
  - UC-complete-sdd-workflow
entrypoints:
  - modules/hub/app/features/project_management/sdd/control.py
  - modules/hub/app/features/project_management/sdd/progress.py
  - modules/hub/app/features/project_management/sdd/decisions.py
  - modules/hub/app/features/project_management/pipeline_runs/api/v1.py
---

# [CAP-SDD-workflow-control] Native SDD workflow control and integration authority

## 1. Summary

The native controller consumes devkit's evaluated stage, requests and envelopes,
then advances the existing PR run. Operator decisions bind inspected evidence;
worker publication and subsequent evaluation determine whether the workflow can
continue. Hub retains integration and merge authority independently of repository
records. `UC-complete-sdd-workflow` follows a bound spec through that process.

## 2. Scope & Boundary

- **In-Scope**: native enrollment binding, stage dispatch, workflow answers,
  worker-question publication, held evidence, integration approval/revocation,
  rework, authorized handoff, recorded report evidence and native resume replay.
- **Out-of-Scope**: `CAP-SDD-native-delivery` owns activity starts and proposal
  acceptance/rejection commits; `CAP-SDD-runtime-isolation` owns isolated evaluation
  and restore; `CAP-PR-operator-decisions` owns shared question/answer storage;
  `CAP-PR-pull-request-delivery` owns PR CI/merge and external delivery recovery.
- **Scope Excluded**: generic resume as approval, fabricated pushes for no-change
  answers, arbitrary workflow rebinding and cancellation of remote work already sent.

## 3. Business Rules & Policies

1. **Bound activity branch**: WHEN enrolling an SDD run, Hub MUST require an existing
   proposal/spec unit on its matching activity branch before attaching native execution.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_enrollment_attaches_only_the_units_activity_branch`, `test_native_enrollment_requires_spec_and_readiness_is_read_only`.
2. **Decision receipt**: WHEN an identical native resume request is replayed, Hub
   MUST return current run state without repeating its transition or replacing
   its durable decision receipt.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_single_owner_approval_to_ci_merge_and_idempotent_receipt`; [test_workflow_decisions.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_workflow_decisions.py), `test_workflow_answer_is_revision_fenced_durable_and_replayed_once`.
3. **Fresh approval basis**: IF approval uses a stale run revision, changed evidence,
   a held gate or the still-unchanged rework head, THEN Hub MUST refuse approval
   with HTTP 409 instead of granting integration authority.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_stale_revision_and_changed_evidence_cannot_approve`, `test_unresolved_worker_problem_blocks_the_run_and_its_approval`.
4. **Resume is inspection**: WHEN generic native resume reinspects a wait, Hub MUST
   preserve the distinction between continuation and integration approval.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_resume_never_means_approval_and_reject_stops`.
5. **Observed or delegated approval**: WHEN unheld integration evidence is ready
   and approval is not withheld, Hub MUST record authorization from an observed
   ready PR or the pinned integration-auto policy before continuing integration.
   Check: [test_hitl.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_hitl.py), `test_ready_pr_records_g3_approval_and_audit`, `test_revoke_cannot_be_undone_by_ready_or_generic_resume`.
6. **Given-channel gate**: WHERE integration uses the `given` answer channel, Hub
   MUST pass recorded authority as `--given dev-integration` without preparing a
   repository decision record for that gate.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_given_integration_gate_is_approved_without_a_decision_record`.
7. **Approval polling boundary**: WHILE a native run has an automatic approval-wait
   marker, Hub MUST keep its paused wait eligible for scheduled reinspection without
   treating an explicit manual pause as such a wait.
   Check: [test_hitl.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_hitl.py), `test_g3_polling_wakes_ready_but_not_manual_pause`, `test_manual_pause_disables_existing_g3_wait`.
8. **Withdrawn readiness**: IF an approval that observed PR readiness encounters a
   return to draft, or an unapproved head change is observed after approval, THEN
   Hub MUST clear authorization and block for renewed inspection.
   Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_draft_reentry_revokes_approval_and_prevents_merge`, `test_unexpected_head_after_approval_is_not_merged`.
9. **Withheld authority**: WHEN approval is explicitly revoked or rework is requested,
   Hub MUST retain withheld authority through later ready observations and generic resume.
   Check: [test_hitl.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_hitl.py), `test_revoke_cannot_be_undone_by_ready_or_generic_resume`; [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_rework_is_a_new_attempt_without_approval`.
10. **Rework proof**: WHEN explicit rework is requested, Hub MUST retain the previous
    head as an outstanding change requirement until a different head is inspected.
    Check: [test_hitl.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_hitl.py), `test_rework_times_out_and_generic_resume_preserves_requirement`.
11. **Selected clarification**: WHEN a saved native run answer is applied, Hub MUST
    propagate that selected question/answer context to subsequent stage requests
    without including unselected alternatives or fabricating a required push.
    Check: [test_hitl.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_hitl.py), `test_applied_question_and_answer_reach_next_stage`, `test_no_change_answer_returns_to_gate_without_fabricated_push`.
12. **Worker hold**: WHILE evaluated worker problems, malformed envelopes or unanswered
    worker questions hold the unit, Hub MUST withhold integration and merge authority.
    Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_unresolved_worker_problem_blocks_the_run_and_its_approval`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_unresolved_problem_blocks_until_a_resolution_envelope`, `test_worker_question_waits_until_an_answer_envelope_exists`.
13. **Worker answer channel**: WHEN an operator answers a worker question, Hub MUST
    retain an answer-envelope instruction with `by: user` for agent publication
    rather than author a generic decision YAML record for that question.
    Check: [test_workflow_decisions.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_workflow_decisions.py), `test_worker_question_is_answered_for_an_answer_envelope_not_a_record`.
14. **Answer validation**: IF a worker question is declined/canceled, a choice is
    outside its options, or an outside-options answer has no decision text, THEN
    Hub MUST refuse that answer with HTTP 422.
    Source: [decisions.py](../../../modules/hub/app/features/project_management/sdd/decisions.py), `validate_answer`; [test_workflow_decisions.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_workflow_decisions.py) checks decline refusal.
15. **Publication before progress**: WHEN a workflow answer is accepted, Hub MUST
    retain the response and prepared publication artifact under the resume receipt
    before dispatching its publication attempt.
    Check: [test_workflow_decisions.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_workflow_decisions.py), `test_workflow_answer_is_revision_fenced_durable_and_replayed_once`; [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_devkit_authors_answer_and_return_and_invalidates_approval`.
16. **Handoff authority**: WHEN accepting a workflow handoff for the same spec
    anchor, Hub MUST record only the selected definition's ID/hash as an authorized
    workflow transition rather than permit arbitrary runtime/policy rebinding.
    Check: [test_cli.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_cli.py), `test_accepted_handoff_authorizes_only_the_selected_definition`.
17. **Stage attempt bound**: WHEN three attempts already exist for the same stage,
    base and run epoch, Hub MUST block another stage dispatch pending inspection.
    Source: [progress.py](../../../modules/hub/app/features/project_management/sdd/progress.py), `SddProgress.dispatch`.
18. **Report provenance**: WHEN retaining worker/support reports, Hub MUST preserve
    their workflow segment, actual effort, support/reverify relationships and scope
    extensions rather than let another workflow's historical worker authorize Planning.
    Check: [test_evidence.py](../../../modules/hub/tests/unit/features/project_management/sdd/test_evidence.py), `test_preserves_every_support_round_its_closing_review_and_actual_effort`, `test_historical_or_other_workflow_workers_cannot_authorize_current_planning`, `test_scope_extensions_preserve_exact_files_reasons_tasks_and_requirements`.
19. **Changed base**: IF a moved base requires integration again, THEN Hub MUST
    return to workflow integration before merging instead of reusing the earlier
    completed integration result.
    Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_base_change_returns_to_integration_without_merging`.
20. **Integration rejection**: WHEN an operator rejects integration, Hub MUST cancel
    the native run while retaining its decision audit and previous external effects.
    Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_resume_never_means_approval_and_reject_stops`, `test_decision_audit_survives_revocation`.

21. **Existing merge owner**: WHEN native workflow evidence becomes merge-ready,
    Hub MUST retain the existing PR executor for CI and policy-controlled merge
    rather than introduce a second merge controller.
    Check: [test_native.py](../../../modules/hub/tests/integration/features/project_management/sdd/test_native.py), `test_single_owner_approval_to_ci_merge_and_idempotent_receipt`.

### Exact native decision discovery

WHEN listing native decisions, Hub MUST derive supported worker, workflow, proposal and integration subjects from persisted devkit-spec owner evidence. Unsupported snapshots/kinds are excluded. Held requests do not create competing actionable gates; existing approval or proposal publication excludes a duplicate integration/proposal action. Recorded worker answers remain nonactionable publication-pending subjects until validated answer-envelope evidence resolves that exact worker/question. Check: [discovery.py](../../../modules/hub/app/features/project_management/sdd/discovery.py) and `test_native_generation_and_publication_pending` in [test_discovery.py](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_discovery.py).

WHEN native evidence head/base, workflow/runtime/policy, binding or request content changes, Hub MUST create a new discovery fingerprint with First observed waiting age. Native Hub questions additionally retain their own question identity/head. Unchanged generations retain waiting age; evidence observation time comes from actual owner inspection, including through unrelated bookkeeping writes. Backfill records observation time without reconstructing historical native wait. Check: `test_native_hub_question_tracks_inspected_generation`, `test_native_observation_age_changes_only_after_inspection` and `test_discovery_backfill_roundtrip`.

WHEN Review selects a native subject, Hub MUST inspect outside the database transaction and persist the replacement evidence only after run revision/epoch and project revision/binding CAS succeeds. An obsolete selection returns 409 after committing its replacement basis; an inspection race discards stale results. Explicit Review of the replacement is required. Nonactionable publication rows refuse Review. The adapter never advances, dispatches, answers, publishes or grants approval. Check: `test_native_review_persists_replacement_and_cas_discards_race`.

IF inspection discovers a changed protected head or returned-to-draft PR, THEN Hub MUST apply the same authority revocation guard as scheduled observation before storing replacement evidence. Published-plan and authorized-head-change exceptions retain their owner semantics. Check: `test_review_withholds_stale_native_authority` and existing native observation tests.

`CAP-PR-operator-decisions` defines the shared listing/review transport. `UX-decision-inbox` routes exact subjects to `UX-run-decisions`, `UX-sdd-workflow-request` and `UX-sdd-run`; selecting a non-first request never substitutes the first request.

### Outcome disclosure

WHEN reading a worker-answer outcome, Hub MUST correlate its exact recorded operation, source worker-envelope filename and question ID against the original retained workflow/segment and inspected basis. Matched publication proof is retained in its existing receipt during owner inspection. A later workflow position does not erase that proof. Legacy receipts without sufficient original context remain unknown. Check: `test_exact_native_answer_requires_matching_envelope_and_current_context` and `test_answer_publication_never_uses_a_later_subject` in [test_outcomes.py](../../../modules/hub/tests/integration/features/project_management/pipeline_runs/test_outcomes.py).

WHILE the exact worker answer is recorded without resolved publication, its controls MUST reject duplicate UI submission using persisted owner records or an acknowledged exact in-memory intent, including failed outcome/owner reads and reload. Missing requests or unrelated envelopes do not prove publication. Check: [SddWorkflowRequests.integration.test.ts](../../../modules/hub-ui/src/lib/features/project-management/pipeline-runs/SddWorkflowRequests.integration.test.ts).

WHEN showing a historical integration receipt, Hub MUST disclose current authority and holds separately. Neither generic resume nor a successful receipt grants fresh authority. The shared owner lookup is defined by `CAP-PR-operator-decisions`; `UX-sdd-run` shows these independent facts.

## 4. Interfaces & Data Contracts

Native enrollment uses `POST /api/v1/projects/{project_id}/runs` with an existing
`pull_number` and `spec_dir`; optional `activity_effort` is `low`, `medium` or
`high`. A spec unit uses `dev-<slug>`; a proposal activity uses its matching
Planning/Development branch. `CAP-SDD-native-delivery` owns creation and proposal
decisions. `CAP-SDD-runtime-isolation` owns runtime checks and snapshot drift.

`POST /api/v1/pipeline-runs/{run_id}/resume` requires UUID `request_id` and
`expected_revision`. Native controls accept exactly one of:

| Input | Meaning |
| --- | --- |
| No direction input | Reinspect/continue, without granting approval |
| `decision: approve` | Authorize the inspected integration basis |
| `decision: revise`, nonblank `feedback` | Request changed implementation and renewed workflow evidence |
| `decision: revoke` | Block and withhold integration authority |
| `decision: reject` | Cancel integration, not proposal rejection publication |
| `answer_id` | Apply one stored run clarification; shared storage belongs to `CAP-PR-operator-decisions` |
| `workflow_answer: {request, action, value?}` | Answer one current workflow request, with optional `feedback` |

New controls check current local run/project identity and revision. Approval,
rework and answer paths also read fresh PR/workflow evidence. Revoke and reject
use retained evidence without requiring that remote evaluation. Revoke can apply
while the run is active; other direction controls require paused/blocked state. Ended runs
refuse new mutation, while matching receipts replay current state. Reuse with
changed payload/actor conflicts. State/evidence/identity conflicts use HTTP 409 /
`CONFLICT`; invalid combinations, choices and missing rework text use HTTP 422 /
`INVALID_REQUEST`. Legacy-provider snapshots are read-only and require a new run.

Generic workflow actions are `accept`, `decline` and `cancel`. A workflow `cancel`
records deferral; it is not native run cancellation or approval revocation.
`gate:dev-integration` uses the integration controls, and `gate:plan-accept` uses
proposal controls. For worker questions (`question:*` or `answer: envelope`),
only `accept` is valid. A supplied choice must match an option; a null choice
requires decision text. Hub retains the actual authenticated actor separately
from the envelope's `by: user` authority.

For record-channel answers, the pinned CLI prepares the exact unit-relative YAML;
Hub refuses unsafe artifact paths. Publication instructions use
`autohub-decision:<UUID>` for idempotence, preserve occupied filenames and require
agent commit/evaluation before progress. Worker answers use
`devkit workflow envelope answer --unit <unit> --answers-to <worker> --answers-file <file>`.
Rework can prepare `devkit workflow return --to <stage>`; later approvals/reports
are then invalidated by that recorded return, not by a stale-approval notice alone.

At `dev-integration`, Hub can authorize through explicit approval, observed
readiness (`github:pr-ready`) or pinned auto policy. A draft can integrate under
explicit/policy authority but cannot merge until ready. `auto_merge=false` still
prevents automatic merge. Applying a stored run clarification at/after integration withholds automatic
approval; earlier implementation clarifications retain their configured policy. Generic
resume, repository decision records and ready status do not undo withheld authority.

Approval waits are paused and consume no execution slot; marked waits poll at a
five-minute internal due time subject to dispatcher ticks. Manual pause and
pending questions do not auto-resume. Rework/decision publication waiting on the
same head, or an unchanged active stage, blocks after 45 minutes from the active
attempt's start; generic resume preserves the rework requirement. A moved base
can require reintegration within the existing approved intent, not a fabricated
blanket requirement for another human approval.

Evidence includes inspected head/base, workflow/current gate, final-report and
support rounds, `activity_effort` and `scope_extensions` (path, task ordinal,
reason, requirement IDs). Review gaps are guidance; the CLI remains the gate
source. Native agent-reply questions are collected after a push using the delivered
attempt/head marker and bind to the observed head. Applied direction is appended
to later stage instructions chronologically; unapplied answers do not become work.
`GET /api/v1/pipeline-runs/{run_id}/sdd-decisions` exposes up to 100 decision records.

## 5. Source and Verification Boundary

The contract derives from [control.py](../../../modules/hub/app/features/project_management/sdd/control.py),
[progress.py](../../../modules/hub/app/features/project_management/sdd/progress.py),
[decisions.py](../../../modules/hub/app/features/project_management/sdd/decisions.py),
[evidence.py](../../../modules/hub/app/features/project_management/sdd/evidence.py)
and [schemas](../../../modules/hub/app/features/project_management/pipeline_runs/interaction_schemas.py).
Tests above identify inspected regression evidence; the source-only stage-attempt
bound and full answer-validation/path matrix are not claimed as individually
executed coverage. Live provider questions, agent publication and serving-host
CI/merge still require the operational canary.

## 6. Batch-origin work

WHEN a native activity originates in an SDD batch, Hub MUST preserve the same per-run workflow decisions and integration authority as an individual activity. A batch receipt, dependency result, pause/resume or retained run link grants no approval and performs no handoff or merge. Check: `modules/hub/tests/integration/features/project_management/sdd/test_batch_progression.py`.

`UC-execute-sdd-batch` exposes read-only original/current anchor, claim, PR and owner evidence through `UX-sdd-batch`. The operator opens `UX-run-decisions`, `UX-sdd-run` or `UX-sdd-workflow-request` for existing owner controls. `UC-complete-sdd-workflow` continues unchanged for that exact owner. Shared start reservations and atomic exact enrollment binding belong to `CAP-SDD-native-delivery`; they do not create a second executor.
