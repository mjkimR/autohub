---
id: OPS-sdd-activity-start-refusals
title: "SDD activity start refusal and uncertain publication routing"
status: active
summary: "Routes a refused or uncertain repository-owned SDD activity start, and a refused claim reconciliation, to existing owners by comparing the HTTP status, error code and detail with the retained activity claim; it excludes progression of a Run after a successful start."
related_capabilities:
  - CAP-SDD-native-delivery
related_usecases:
  - UC-start-sdd-activity
---

# [OPS-sdd-activity-start-refusals] SDD activity start refusal and uncertain publication routing

A Planning or Development start returns HTTP `409` or `422`, or loses its response, and the operator cannot tell
whether to fix configuration, retry, follow another owner or release a reservation. Most start conflicts share the
generic code `CONFLICT`, so the code alone does not separate a recoverable retry from a retained external owner.
The retained activity claim decides it: its `run_id`, `settled` flag and `checkpoint` fields (`uncertain`,
`lease_expires_at`, `refusal`, `reconciliation`, `pull_number`) show which owner acts next.

## Routing

A refusal raised after the claim exists ends its `detail` with `; inspect /api/v1/projects/<project-id>/sdd/claims/<claim-id>`.
Read that claim with `GET /api/v1/projects/<project-id>/sdd/claims/<claim-id>`; it returns `run_id`, `settled`,
`checkpoint_digest` and `checkpoint` without the lease token. A refusal without that suffix was raised before any
claim existed.

| Symptom or state | Discriminating evidence | Next useful owner |
| --- | --- | --- |
| Start refused for project configuration | HTTP `422` `INVALID_REQUEST` with `Select sdd project mode first`, `Enable the project and connect its GitHub repository` or a catalog refusal; the detail has no claim path | `UC-start-sdd-activity` extension 2a; `CAP-SDD-native-delivery` rule 4 (Host admission) |
| Start refused for a missing base, and retrying the same request returns the same refusal | HTTP `422` `Base branch <name> is not on the remote` with a claim path; the claim shows `settled` `true` and `checkpoint.refusal`, because no branch or PR write was attempted | `UC-start-sdd-activity` extension 2a; a corrected start is a new request under `CAP-SDD-native-delivery` §4 |
| Unit already has an owner bound to a Run | HTTP `409` `SDD_ACTIVITY_OWNED` names `owner claim <claim-id>`; that claim has a non-null `run_id` | `UC-complete-sdd-workflow`, followed through the bound Run; `UX-sdd-claim-recovery` active state |
| Unit has an uncertain owner without a Run | HTTP `409` `SDD_ACTIVITY_OWNED`; the claim has `run_id` `null`, `checkpoint.uncertain` `true` and no future `lease_expires_at` | `UC-start-sdd-activity` extension 2b; [inspect and reconcile](../runbooks/sdd-runtime.md#inspect-and-reconcile-uncertain-publication) |
| Activity branch belongs to someone else | HTTP `409` `SDD_BRANCH_EXISTS`; the remote `plan-<slug>` or `dev-<slug>` head differs from the claim's `checkpoint.initial_sha`, or the claim has none | `UC-start-sdd-activity` extension 3a; `CAP-SDD-native-delivery` §4 (an existing branch remains a conflict) |
| Publication outcome unknown after a lost or failed response | HTTP `409` `CONFLICT` with `outcome is uncertain`, `ambiguous`, `history is incomplete`, `is absent` or `is missing` and a claim path; the claim has `checkpoint.uncertain` `true` with `ref_attempted` or `pr_attempted` | `UC-start-sdd-activity` extension 3b; [uncertain activity publication](../runbooks/sdd-runtime.md#uncertain-activity-publication), then [inspect and reconcile](../runbooks/sdd-runtime.md#inspect-and-reconcile-uncertain-publication) |
| PR published but no Run returned | HTTP `409` `CONFLICT` with `Saved enrollment intent differs` or `enrollment ... requires reconciliation`; the claim has `checkpoint.pull_number` and `run_id` `null` | `UC-start-sdd-activity` extension 4a; `CAP-SDD-native-delivery` rule 7 (Exact recovery) |
| Retry refused while another attempt runs | HTTP `409` `Activity reconciliation is already in flight`; the claim's `checkpoint.lease_expires_at` is in the future | `CAP-SDD-native-delivery` §4 (retry with the same request UUID and payload) after the lease expires |
| Retry refused as a different request | HTTP `409` `Request identity already binds a different actor or payload` or `Start request belongs to another activity owner`; the request UUID was reused with another payload, actor, unit or activity | `CAP-SDD-native-delivery` §4 (a start retry reuses its UUID and identical payload); [uncertain activity publication](../runbooks/sdd-runtime.md#uncertain-activity-publication) |
| Retry refused after a project edit | HTTP `409` `Project changed after activity claim`; the claim's `checkpoint.project` differs from the project's repository, connector, catalog, revision, automation, enabled flag or type | `CAP-SDD-native-delivery` rule 10 when `checkpoint.uncertain` is `true`; otherwise the no-row fallback below |
| Retry of a finished claim refused | HTTP `409` `Activity already settled ... Replay creates no new activity`; the claim shows `settled` `true` | `UX-sdd-claim-recovery` settled state; a new start is a new request under `UC-start-sdd-activity` |
| Reconciliation refused as ineligible | HTTP `409` `Only an uncertain activity without a Run or live lease can be settled`; the claim has a `run_id`, no `checkpoint.uncertain` or a future `lease_expires_at` | `CAP-SDD-native-delivery` rule 10 (Uncertain reservation); `UX-sdd-claim-recovery` active state |
| Reconciliation refused for changed evidence | HTTP `409` `Claim evidence changed; inspect the retained candidate again`; the current `checkpoint_digest` differs from the submitted `expected_checkpoint_digest` | [inspect and reconcile](../runbooks/sdd-runtime.md#inspect-and-reconcile-uncertain-publication) |
| Reconciliation refused as a different acknowledgment | HTTP `409` `Claim reconciliation already records a different request`; `checkpoint.reconciliation.request_id` differs from the submitted `request_id` | `UX-sdd-claim-recovery` settled state; the recorded acknowledgment stands |

For evidence that matches no row, keep the original request UUID and payload, read the claim named in the detail,
and take the claim's `run_id`, `uncertain` and `lease_expires_at` facts to `CAP-SDD-native-delivery` §4, which
owns retry, conflict and release eligibility.

## Normal-state observation

A start returns HTTP `201` with a Run whose branch is `plan-<slug>` or `dev-<slug>` and whose PR is a Draft. Its
claim shows that `run_id` and `checkpoint.uncertain` `false`. A released reservation shows `settled` `true` and a
`checkpoint.reconciliation` record. `CAP-SDD-native-delivery` owns these facts; Run progression after the start
belongs to `UC-complete-sdd-workflow`.

## Authority boundary

The claim records Hub's publication checkpoints, not the remote outcome. It cannot show whether an external agent
is still working on a saved branch or PR, which the operator inspects in GitHub before acknowledging external work.
A claim that is neither uncertain, settled nor bound to a Run, and whose project basis changed, has no documented
release path in `CAP-SDD-native-delivery`.

## Update triggers

- `CAP-SDD-native-delivery` rules 4, 7 or 10, or its §4 retry and release contract, change.
- The refusal codes `SDD_ACTIVITY_OWNED` or `SDD_BRANCH_EXISTS`, or the claim fields `run_id`, `settled`,
  `uncertain`, `lease_expires_at`, `refusal` or `reconciliation`, change.
- The refusal sites in [activities.py](../../modules/hub/app/features/project_management/sdd/activities.py),
  [activity_claims.py](../../modules/hub/app/features/project_management/sdd/activity_claims.py) or
  [claim_history.py](../../modules/hub/app/features/project_management/sdd/claim_history.py) change.
