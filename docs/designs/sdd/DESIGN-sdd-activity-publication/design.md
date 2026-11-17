---
id: DESIGN-sdd-activity-publication
title: "SDD activity publication and its claim checkpoint"
status: active
area: sdd
summary: "Explains the order in which a Planning or Development start publishes its intent commit, branch, Draft PR and Run, and the activity claim checkpoint each later retry, reconciliation and settlement reads back; eligibility and retry guarantees stay with CAP-SDD-native-delivery."
related_capabilities: [CAP-SDD-native-delivery]
related_usecases: [UC-start-sdd-activity, UC-complete-sdd-workflow]
related_operations: [OPS-sdd-activity-start-refusals]
entrypoints:
  - modules/hub/app/features/project_management/sdd/activities.py
  - modules/hub/app/features/project_management/sdd/activity_claims.py
  - modules/hub/app/features/project_management/sdd/claim_history.py
  - modules/hub/app/features/project_management/sdd/claim_policy.py
---

# [DESIGN-sdd-activity-publication] SDD activity publication and its claim checkpoint

A Planning or Development start writes to GitHub three times (a commit, a ref and a Draft PR) and then enrolls a
Run, and a lost response can interrupt it between any two of those writes. Hub cannot tell an absent effect from an
unobserved one, so before each write it records what it is about to do in the activity claim's `checkpoint`. That
record decides whether a retry continues, returns a stored refusal, or waits for an operator's reconciliation. The
retry, conflict and release guarantees belong to `CAP-SDD-native-delivery` §4; this design explains the order and
the record behind them.

## Reservation and execution lease

`SddUseCase.start_activity` in
[usecases.py](../../../../modules/hub/app/features/project_management/sdd/usecases.py) checks project mode,
connection and catalog, then calls `ActivityClaims.reserve` in
[activity_claims.py](../../../../modules/hub/app/features/project_management/sdd/activity_claims.py) inside the same
project-locked transaction.

- A claim with the same `(project_id, request_id)` is returned only if its actor and request digest match, and only
  for the same unit and activity.
- Otherwise a live claim for the same unit and activity refuses the start with `SDD_ACTIVITY_OWNED`.
- Otherwise a new claim stores the project basis and the start request in its checkpoint.

`ActivityClaims.execute` then takes a fresh transaction, locks the project and the claim, and reads the checkpoint
in this order:

1. A bound `run_id` returns that Run and clears `uncertain`.
2. A stored `refusal` is raised again, unchanged.
3. A settled claim refuses with `Activity already settled`.
4. A future `lease_expires_at` refuses with `Activity reconciliation is already in flight`.
5. A changed project basis refuses with `Project changed after activity claim`. A claim not yet marked uncertain is
   first recorded the way a failed start is: `refusal` and `settled` when neither `ref_attempted` nor `pull_number`
   is present, otherwise `uncertain`. An already uncertain claim is left unchanged, so its `checkpoint_digest` stays
   stable for reconciliation.
6. Otherwise the claim gets a new random `lease` token that expires five minutes later.

Every later checkpoint write locks the project and the claim again. The write is refused unless the lease token is
unchanged and unexpired and the project basis still matches.

## Publication order

`ActivityStarter.start` in
[activities.py](../../../../modules/hub/app/features/project_management/sdd/activities.py) runs all GitHub calls
under one 90-second timeout. It receives the saved checkpoint, so a retry resumes from the saved facts instead of
starting over.

1. Read the base ref, the `plan-<slug>` or `dev-<slug>` activity branch and up to ten pages of PRs for that branch.
   A candidate PR is owned only if its body contains `<!-- autohub-sdd-activity:<activity>:<slug> -->` and its head
   ref, base ref and both repositories match.
2. Refuse when the evidence disagrees with the checkpoint. For example, an existing branch whose head is not
   `initial_sha` gives `SDD_BRANCH_EXISTS`, and more than one owned PR is ambiguous.
3. If no branch exists and no `initial_sha` is saved, create a commit with the base commit's tree and the base as
   its only parent. The commit message is `Start <Planning|Development> of PROP-<slug>` followed by
   `AutoHub request: <request_id>`. Retain `initial_sha`, `branch` and `base_sha`. The commit changes no file, so
   the Draft PR can be opened without editing proposal content.
4. Re-read the base ref and refuse with `Base moved before activity publication` if it changed.
5. Retain `ref_attempted`, create `refs/heads/<branch>` at `initial_sha`, then retain `ref_published`.
6. If no owned PR exists, retain `pr_attempted`, then create a Draft PR titled `<Planning|Development>: PROP-<slug>`
   whose body ends with the marker. Retain `pull_number`.
7. Retain `enrollment_request` (PR number, unit, effort, catalog, handoff) and enroll the PR. A saved
   `enrollment_request` that differs from the rebuilt one refuses with `Saved enrollment intent differs`.

Enrollment calls `bind_enrollment` in its own transaction, from
[lifecycle.py](../../../../modules/hub/app/features/project_management/pipeline_runs/usecases/lifecycle.py).
It sets `run_id` only if the Run's branch, PR number, head SHA, repository, connector and descriptive snapshot match
the checkpoint. The claim and the Run are therefore bound before any response can be lost. `execute` then clears
`lease_expires_at` and `uncertain`.

A saved `ref_attempted` or `pr_attempted` without the matching remote ref or PR refuses with an `outcome is
uncertain` conflict, because Hub cannot prove the earlier request did nothing.

## Failure recording

When `start` raises, `execute` records the failure only while it still holds a valid lease.

- If neither `ref_attempted` nor `pull_number` was retained, nothing reached a ref or PR. The checkpoint gets
  `refusal` (`status`, `code`, `detail`; HTTP `503` for an unexpected exception), the claim is settled and a retry of
  the same request returns that refusal.
- Otherwise the checkpoint gets `uncertain: true`, `uncertainty_observed_at` and `last_error`, and the lease is
  cleared. A retry with the same request resumes from the saved facts. `SddClaimHistory.reconcile` can release the
  reservation once no lease is live.

Two other writers settle claims. `settle_individual_claims`, run from shared maintenance through
[activity_history.py](../../../../modules/hub/app/features/execution/tasks/domains/maintenance/activity_history.py),
settles up to 20 claims per pass whose bound Run reached a final state, and stores `outcome`.
`SddClaimHistory.reconcile` in
[claim_history.py](../../../../modules/hub/app/features/project_management/sdd/claim_history.py) settles an
uncertain claim without a Run or live lease, and stores `reconciliation`.

## Claim datasheet

Location: table `sdd_activity_claims`, one row per start request. `CAP-EXEC-scheduling-maintenance` §6 owns
their retention.

| Column | Meaning |
| --- | --- |
| `project_id`, `request_id` | Unique together; the client's start request UUID |
| `actor`, `request_digest` | Replay identity of the start request |
| `unit`, `activity` | `docs/proposals/PROP-<slug>` and `plan` or `dev`; unique among claims with `settled = false` |
| `settled` | No further publication or release for this claim |
| `run_id` | Bound Run, set by `bind_enrollment` |
| `checkpoint` | JSON object below |

`checkpoint` fields, in the order they are first written:

| Field | Writer | Meaning |
| --- | --- | --- |
| `project` | `reserve` | Project basis: `repository`, `connector_id`, `project_revision`, `catalog_id`, `automation`, `enabled`, `type` |
| `request` | `reserve` | The start request as JSON |
| `lease`, `lease_expires_at` | `execute` | Execution lease token and ISO-8601 expiry; the expiry is set to null when the attempt ends |
| `initial_sha`, `branch`, `base_sha` | `start` | The intent commit and where it belongs |
| `ref_attempted`, `ref_published` | `start` | Before and after the ref creation request |
| `pr_attempted` | `start` | Before the Draft PR creation request |
| `pull_number` | `start` | The owned Draft PR |
| `enrollment_request` | `start` | The exact enrollment payload |
| `run_id` | `bind_enrollment`, `execute` | String copy of the bound Run |
| `uncertain`, `uncertainty_observed_at`, `last_error` | `execute` | Publication may have had an unrecorded effect |
| `refusal` | `execute` | Stored refusal of a claim settled before any ref or PR write |
| `outcome` | maintenance | Final Run `state`, `run_id`, `pull_number`, `pull_url` |
| `reconciliation` | `reconcile` | `request_id`, `actor`, `request_digest`, `checkpoint_digest`, `reconciled_at` |

`request_digest` and `checkpoint_digest` use `request_digest` in
[requests.py](../../../../modules/hub/app/features/project_management/pipeline_runs/requests.py): the lowercase
hexadecimal SHA-256 of Python `json.dumps` with sorted keys, `(",", ":")` separators and default ASCII escaping.
`checkpoint_digest` covers the whole stored checkpoint, including `lease`. `GET .../claims/{claim_id}` omits `lease`
from the checkpoint it returns, so a client copies the returned `checkpoint_digest` into
`expected_checkpoint_digest` instead of recomputing it. Any checkpoint write between the read and the reconciliation
changes the digest and refuses the reconciliation with `Claim evidence changed`.

## Worked example

`test_uncertain_optimistic_publication_can_be_explicitly_settled_without_replacement` in
[test_optimistic_api.py](../../../../modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py)
stores this checkpoint on a claim without a Run (`lease_expires_at` is null or past):

```json
{"uncertain": true, "pr_attempted": true, "initial_sha": "bbbb…bbbb", "branch": "dev-demo", "ref_attempted": true, "lease_expires_at": null}
```

The claim view shows `settled: false` and a `checkpoint_digest`. Posting that digest with a new `request_id` and
`acknowledge_external_work: true` settles the claim with no GitHub call. The response keeps `initial_sha` and
`branch`, adds `reconciliation`, and has `run_id: null`. Repeating the same body returns the same response.

## Authority boundary

- `CAP-SDD-native-delivery` rules 4, 6, 7 and 10 and §4 own admission, Draft publication, exact recovery, retry,
  conflict and release eligibility.
- `CAP-PR-pull-request-delivery` owns the Run after `bind_enrollment`.
- `CAP-EXEC-scheduling-maintenance` §6 owns retention of unresolved claims.
- `OPS-sdd-activity-start-refusals` routes refusals by the fields above.

## Update triggers

- `ActivityStarter.start`, `ActivityClaims.execute`, `bind_enrollment`, `settle_individual_claims` or
  `SddClaimHistory.reconcile` change their write order, lease duration or a checkpoint field.
- `project_basis` or `request_digest` changes what it covers or how it encodes.
- The `GET /claims/{claim_id}` or `POST /claims/{claim_id}/reconcile` interface in `CAP-SDD-native-delivery` §4
  changes.
- Recheck the worked example with
  `just test modules/hub/tests/integration/features/project_management/sdd/test_optimistic_api.py`.
