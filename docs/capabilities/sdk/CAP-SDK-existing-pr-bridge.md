---
id: CAP-SDK-existing-pr-bridge
title: Verified Existing-PR Delivery Bridge
summary: "Configured native SDK tasks verify repository evidence and obtain scoped approval before resuming one existing paused PR run. The bridge observes the existing PR owner and preserves its resume identity through recovery."
area: sdk
status: active
usecases:
  - UC-resume-verified-pr
entrypoints:
  - modules/hub/app/features/execution/flows/bridge.py
  - modules/hub/app/features/execution/flows/evidence.py
---

# [CAP-SDK-existing-pr-bridge] Verified Existing-PR Delivery Bridge

## 1. Summary

The bridge connects an external SDK flow to a `PipelineRun` that was already
implemented outside Hub's native SDD execution. It validates the actual checkout,
claims the PR run, binds approval to evidence and resumes the existing owner.
`CAP-SDK-task-flow-execution` owns admission, machine scopes, approval commands,
worker leases and the surrounding flow lifecycle.

## 2. Scope and Boundary

- **In-Scope**: server-selected project/checkout binding; repository evidence
  evaluation; exclusive PR-run claim; persisted approval authority; existing-run
  resume and receipt recovery; owner-state projection and cancellation fencing.
- **Out-of-Scope**: repository implementation belongs to the external developer;
  workflow definitions and readiness evaluation belong to devkit-spec; ready
  status, CI observation and merging belong to the existing PR owner; checkout
  provisioning and runtime installation belong to the operator.
- **Scope Excluded**: new PR/run creation, a second merge controller, caller-chosen
  checkout roots, bypassing approval by omitting the approval step, and rolling
  back external requests or effects already delivered.

## 3. Business Rules and Policies

1. **Configured namespace**: WHEN a native bridge release is registered, the host MUST restrict its target to a server-configured provider/environment, project and absolute checkout. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_one_flow_claims_pipeline_and_native_namespace_is_restricted`.
2. **Checkout identity**: WHEN repository evidence is read, the bridge MUST require a clean checkout at the requested Git HEAD before and after evaluating evidence. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_real_git_cli_evidence_rejects_dirty_and_changed_head`.
3. **Workflow readiness**: WHEN the check task evaluates the bound spec, the bridge MUST require the configured runtime's evaluated workflow to satisfy Hub's integration-approval readiness predicate. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_real_git_cli_evidence_rejects_dirty_and_changed_head` and its real-CLI fixture.
4. **Paused owner**: WHEN evidence is claimed, the bridge MUST require the configured project's externally implemented PR run to be paused at the supplied revision and head. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_bridge_resumes_once_then_observes_existing_pr` and its `paused` fixture.
5. **Single claim**: IF another flow owns an unreleasable PR claim, THEN the bridge MUST fail the check with `pr-owned-by-another-flow`. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_one_flow_claims_pipeline_and_native_namespace_is_restricted`.
6. **Scoped approval**: WHEN the flow's approval command authorizes a claimed PR, the host MUST persist the approving flow revision, evidence-content digest and machine/key actor on the claim. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_bridge_resumes_once_then_observes_existing_pr`.
7. **No implicit approval**: IF a delivery task has no persisted claim approval, THEN the bridge MUST fail with `pr-resume-approval-required`. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_native_bridge_requires_persisted_scoped_approval`.
8. **Approved evidence**: WHEN a delivery attempt first resumes a PR, the bridge MUST re-evaluate repository evidence against the evidence digest passed from the check task. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_approval_evidence_change_and_cancel_fence`.
9. **Live PR head**: IF the PR head changes before its first resume, THEN the existing PR owner MUST reject the resume instead of creating a successful receipt. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_approval_head_change_rejects_resume`.
10. **Resume identity**: WHEN a delivery attempt resumes the PR, the bridge MUST use that attempt's UUID as the existing owner's resume request ID. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_bridge_resumes_once_then_observes_existing_pr`.
11. **Effect recovery**: IF a worker dies after the resume effect, THEN a recovered delivery attempt MUST reuse the persisted resume receipt without issuing a second resume. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_pr_resume_effect_survives_worker_death_and_cancel_fences_owner`.
12. **Owner projection**: WHEN the PR owner is observed after resume, the bridge MUST project its pending, paused/blocked, failed/canceled or completed outcome into the existing SDK attempt. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_pr_owner_state_is_projected`.
13. **Cancellation fence**: WHEN the owning bridge task is canceled, the bridge MUST tombstone its PR claim against later resume. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_pr_resume_effect_survives_worker_death_and_cancel_fences_owner`.
14. **Owner cancellation**: WHEN a bridge task is canceled after assigning its delivery attempt, the bridge MUST request cancellation of its nonterminal PR owner. Check: `modules/hub/tests/integration/features/execution/flows/test_bridge.py::test_pr_resume_effect_survives_worker_death_and_cancel_fences_owner`.

## 4. Interfaces and Data Contracts

### Registration and inputs

The native binding targets are `autohub.sdd:<name>` for evidence checking and
`autohub.pr_delivery:<name>` for delivery. `AUTOHUB_FLOW_DELIVERY_TARGETS` maps the
name to `provider`, `environment`, `project_id` and an absolute `checkout` path.
Registration rejects an unknown or mismatched namespace with HTTP 422
`worker-binding`. A release resolves and snapshots that binding; clients do not
supply an arbitrary server checkout path.

The bridge uses the release/run/command HTTP API and scopes from
`CAP-SDK-task-flow-execution`. It exposes no separate public resume endpoint.
The check task receives:

| Field | Contract |
| --- | --- |
| `pipeline_run_id` | Existing PR run UUID |
| `pipeline_revision` | Integer at least 1, matching the paused run |
| `head_sha` | Exactly 40 lowercase hexadecimal characters |
| `spec_dir` | Existing directory matching `specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+` within the configured checkout |
| `evidence_digest` | Optional at input; produced by the check and supplied to delivery |

Unknown bridge input fields are rejected. The check emits these reviewed fields
plus `evidence_digest`. Delivery requires its fields to equal the claim's checked
evidence; the approval must still match the complete checked evidence content.
A claim formerly owned by a failed/canceled flow can be reassigned only if no
delivery attempt was assigned. A PR with its own native SDD snapshot is refused
with `pr-owned-by-native-sdd` rather than given a second execution owner.

### Evidence and approval

The check resolves the spec beneath the checkout and rejects file paths escaping
the spec tree. Through the project's server-assigned runtime profile, it evaluates
`devkit spec policy`, `devkit workflow show`, `devkit workflow next` and detailed
envelope checks. The bound workflow defines its required review, reconcile,
completion and final-report evidence; Hub does not replace that definition with
filename presence checks.

The integration-approval readiness predicate rejects held evidence and requires
the evaluated integration gate to be current or already passed under the
predicate's completed-gate condition. The digest covers `head_sha`, the runtime/
workflow/configuration snapshot and SHA-256 hashes of spec files. Git cleanliness
and HEAD are checked again after evaluation and hashing.

Approval stores the approving flow revision, the digest of the claim's checked
fields and the machine/key actor. It does not itself resume the PR. Before the
first resume, delivery rechecks repository evidence and the existing PR controller
checks the expected PR revision/head. Recovery after a recorded resume uses its
receipt rather than repeating initial checkout/resume effects. Existing owner
checks continue to govern CI and merge after that point.

### Results and failures

The delivery worker emits `pipeline_run_id`, owner `state` and `head_sha`.

| Owner outcome | Worker result | Public flow while observing |
| --- | --- | --- |
| `completed` | `completed` | Completes after flow result validation |
| `failed`, `canceled` | `failed`, error `pr-failed` or `pr-canceled` | `failed` |
| `paused`, `blocked` | `pending`, error `pr-paused` or `pr-blocked` | `waiting` / `external-result` |
| Other nonterminal state | `pending` | `waiting` / `external-result` |

The following failures are asynchronous attempt/run errors, not invented HTTP
routes or refusal statuses:

| Error | Condition |
| --- | --- |
| `spec-path-invalid`, `evidence-path-invalid` | Invalid or escaping spec/evidence path |
| `checkout-head-changed`, `checkout-dirty`, `checkout-check-failed` | Checkout identity or Git check failed |
| `workflow-evaluation-failed`, `workflow-not-ready-for-integration` | CLI evaluation failed or did not reach the required gate |
| `pr-owned-by-native-sdd`, `pr-project-mismatch`, `pr-must-be-paused-at-reviewed-revision`, `pr-head-changed`, `pr-must-be-externally-implemented` | Ineligible existing owner |
| `pr-owned-by-another-flow`, `pr-bridge-canceled`, `pr-bridge-owner-mismatch` | Claim unavailable or fenced |
| `pr-resume-approval-required`, `pr-evidence-mismatch`, `pr-attempt-mismatch`, `approved-evidence-changed` | Approval/evidence/delivery identity does not match |
| `pr-resume-rejected`, `pr-run-missing` | Existing owner refused resume or vanished |
| `bridge-input-or-checkout-invalid` | Invalid bridge model or missing checkout/spec |

Internal transient failures such as `bridge-stale` or `bridge-unavailable` reach
the flow worker's recoverable path as `worker-unavailable`; they do not authorize
redispatch under a new attempt ID. Canceling a delivery with an assigned attempt
can cancel the existing owner; cancellation does not roll back external agent
requests, pushes or merges that already happened.

## 5. Source and Verification Evidence

The contracts derive from the inspected
[bridge](../../../modules/hub/app/features/execution/flows/bridge.py),
[evidence reader](../../../modules/hub/app/features/execution/flows/evidence.py),
[target model](../../../modules/hub/app/features/execution/flows/bridge_config.py),
[approval persistence](../../../modules/hub/app/features/execution/flows/services.py)
and [SDD evaluator](../../../modules/hub/app/features/project_management/sdd/services.py).
The [bridge tests](../../../modules/hub/tests/integration/features/execution/flows/test_bridge.py)
use actual Git and the provisioned devkit CLI for evidence checks, while GitHub
and owner transitions use controlled fixtures. Those tests were inspected during
authoring, not executed by this document. Fixture evidence does not establish live
GitHub CI/merge or production deployment.
