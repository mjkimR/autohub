---
id: ARCH-06-execution
title: Execution and recovery sequences
summary: "Shows scheduler, PR, Work Plan recovery, native SDD, SDK and diagnostic execution paths, including their durable identities, compatible locks and remote-observation fences."
status: active
---

# [ARCH-06-execution] Execution and recovery sequences

## Execution paths

| Path | Durable records | Runtime delegation | Contract owner |
| --- | --- | --- | --- |
| Scheduled task | `ScheduleConfig`, `ScheduleJob` | External trigger claims due work and invokes its registered handler | `CAP-EXEC-scheduling-maintenance` |
| PR delivery | `PipelineRun`, attempts, deliveries and replies | Ticks/events/operator calls enter shared bounded advancement | `CAP-PR-pull-request-delivery` |
| Work Plan | `WorkPlan`, `WorkItem`, typed recovery records/events | Admission creates or attaches a PR, then hands it to the existing PR owner | `CAP-WORK-work-plan-execution` |
| Native SDD | PR activity/request and repository workflow evidence | Isolated evaluation selects a workflow operation; Hub fences its publication and continuation | `CAP-SDD-native-delivery`, `CAP-SDD-workflow-control` |
| SDK task/flow | `sdk_flow_*` releases/runs/steps/attempts/commands | Maintenance advances an immutable admitted release through configured targets | `CAP-SDK-task-flow-execution` |
| Connection diagnostic | Test record, ownership and cleanup evidence | A claimed recipe step prepares, dispatches, observes or cleans up diagnostic work | `CAP-CONN-connection-verification` |

Completing a scheduler invocation does not imply that a delegated PR or SDK flow
has completed. Shared maintenance delegates pending domain work rather than
substituting a second execution owner.

## Ordinary PR observation

```mermaid
sequenceDiagram
    participant Trigger as Tick, event or operator
    participant Hub as PR coordinator
    participant DB as Database
    participant Remote as GitHub or provider
    Trigger->>Hub: Advance the run
    Hub->>DB: Claim and prepare a checkpoint
    DB-->>Hub: Leased run, project and attempt identities
    Hub->>Remote: Observe external state
    Remote-->>Hub: Observation result
    Hub->>DB: Recheck identities and retain the result
    DB-->>Hub: Committed result or stale-continuation refusal
    Hub-->>Trigger: Progress, wait or recoverable failure
```

The observation transaction ends before external I/O. A later write rechecks the
checkpoint in a fresh transaction. If the result enables another ready step,
advancement can continue within its existing invocation budget. Delivery or an
actual wait returns control to a later trigger. CI interpretation and provider
transport are delegated to `CAP-PR-ci-observation` and `CAP-PR-agent-dispatch`.

Webhook acknowledgement precedes completion of this path. The stored delivery
can be processed through the configured queue or bounded recovery;
`CAP-PR-webhook-advancement` owns that intake/continuation boundary.

## Work Item recovery

`ADR-work-item-recovery-lineage` retains the original Item and linked Run. `WorkItemRecovery` stores project-local request uniqueness, actor/reason, normalized command, accepted revisions, immutable prior outcome and mutable progress. `WorkItemRecoveryEvent` appends ordered outcome evidence. A partial unique index admits one pending recovery per Item. Recovery snapshots retain stable execution identities after eligible Run pruning; legacy Items receive no synthetic recovery rows.

Recovery MUST commit its intent and lease generation before remote I/O, and recheck Plan/Run revisions, Item lease token/expiry and recovery generation before applying observations. Check: `test_expired_recovery_observation_cannot_activate`, control-during-I/O regressions and PostgreSQL recovery races in the Work Plan integration suite. Source: `modules/hub/app/features/project_management/work_plans/recovery_tick.py`.

Request acceptance and terminal recovery apply Project → Plan → Run → Item locks; terminal admission then locks the catalog. Ordinary preparation admission uses Project → Plan → catalog and never locks a Run. Existing delivery locks Run before catalog. Observation/retention uses Run → Item and never acquires Project/Plan afterward. Item-only lease writes acquire no parent afterward. These orders MUST remain compatible when both owners operate on one Item. Check: PostgreSQL Work Plan/PR integration suites, including ordinary enrollment winning during recovery I/O; review also checks acquisition order.

The recovery worker releases DB locks for PR/ref/comment reads. Pending records stay outside ordinary Item observation; the recovery due queue filters leases/holds before its bounded limit. Once preparation is admitted, the existing preparer owns it. Historical started-work metadata remains set while waiting, preserving the specification edit fence. Terminal activation and its durable intent commit together; active-owner uniqueness prevents a losing recovery from dispatching. The existing PR owner then controls delivery, current-head CI and final merge. A recovery-confirmed last-Item merge invokes ordinary Plan completion and mirror reflection in the same transaction.

## Native decision publication

Native proposal decisions use a different transaction sequence:

1. Retain the request identity and prepare its candidate repository commit.
2. Recheck publication authority and hold the Run/Project fence for the bounded push.
3. Retain the published candidate and apply continuation only if it remains applicable.
4. After an uncertain push/result write, reconcile the exact remote candidate
   rather than repeat publication or restore withdrawn authority.

`CAP-SDD-native-delivery` owns proposal decisions;
`CAP-SDD-workflow-control` owns workflow answers, handoff and integration actions.
`CAP-SDD-runtime-isolation` owns the evaluation process and identity inputs.
The general identity/fencing concepts and deliberate transaction exceptions are
collected in `ARCH-08-crosscutting-concepts`.

## SDK dispatch and PR handoff

Release registration and run admission retain the definition/binding snapshot.
A maintenance step then commits attempt intent, calls the bound worker outside
the database transaction and fences the returned result. Recovery inspects the
same attempt before deciding whether another submission is permitted.

The existing-PR bridge inserts a repository-evidence check and scoped approval
before resuming the existing PR owner. A retained resume receipt lets recovery
follow the same PR attempt. The SDK flow projects that owner's outcome; it does
not replace its ready/CI/merge handling. Exact conditions are in
`CAP-SDK-existing-pr-bridge`.

## Diagnostic completion and housekeeping

A diagnostic step records its verification result separately from resource
cleanup. Shared maintenance can continue unresolved cleanup after the initiating
schedule or page is gone. The diagnostic coordinator and provider recipe remain
responsible for ownership proof and current step identity throughout that work.

Notice delivery reports a retained outcome and has its own acknowledgement;
it does not change the work's authorization. Rate limits, connector rejection
and provider admission holds return control to their owning path's retry/wait
policy. `CAP-NOTIFY-operator-notifications` owns the outbound report, while the
execution capability owns the actual next action.

Implementation anchors include
[PR progress](../../modules/hub/app/features/project_management/pipeline_runs/usecases/progress.py),
[SDD publication](../../modules/hub/app/features/project_management/sdd/plan_publication.py),
[SDK runtime](../../modules/hub/app/features/execution/flows/runtime.py) and
[connection coordination](../../modules/hub/app/features/project_management/connection_tests/services.py).
`ARCH-10-quality-requirements` connects these sequences to measurable regression
scenarios; [deployment status](../operations/deployment-status.md) retains live evidence.

## Sequential SDD admission and recovery

`SddBatch` and `SddBatchMember` retain immutable through-Development selection, source basis, exact order and phase checkpoints. `SddBatchControl` retains revisioned request receipts. `SddActivityClaim` is shared by individual and batch starts. `ADR-sdd-batch-ledger` records this ownership choice; `CAP-SDD-native-delivery` owns the interface.

Batch admission and controls MUST lock Project before Batch and the shared activity reservation. Claim-only lease writes acquire no parent afterward. Existing PR owners retain their Run transaction; exact claim binding is validated and written atomically in enrollment, including project, lease, unit, repository, branch, candidate and enrollment snapshot. No Run lock is held while acquiring a parent Project/Batch lock. Check: PostgreSQL multi-connection `modules/hub/tests/integration/features/project_management/sdd/test_batch_claims.py`; lock-order review complements these races.

Sequential admission MUST retain one member's slot through its exact Planning/Development owner outcomes. A claim is committed before remote effects; its exact candidate is saved before push. A final selected-base read follows policy evaluation before the bounded publication under its claim fence. Recovery reuses only saved artifacts and a live matching lease. Enrollment response loss recovers the exact persisted binding. Missing artifacts or uncertain ownership preserve the hold; retired settled receipts never restart. Check: `test_batch_claims.py` and `modules/hub/tests/unit/features/project_management/sdd/test_batch_activities.py`.

A maintenance transition observes the existing owner or performs one next phase admission. Planning merge/accepted-source evidence precedes Development; validated handoff identifies the exact SPEC; completed SPEC and confirmed Development merge finish a member. Canonical edge-only repair preserves all other graph/content identities. These checks grant no workflow or merge authority. Check: `modules/hub/tests/integration/features/project_management/sdd/test_batch_progression.py`.

Unresolved claims protect their runs from retention. Settled claims retain tombstones after eligible run-link pruning. The migration freezes four explicit table definitions and indexes rather than importing changing application metadata. Check: `modules/hub/tests/integration/migrations/test_sdd_batch_migration.py`.

## Work Item replacement evidence

`ReplacementLink`, `ReplacementAcceptance`, `ReplacementEvent`, `ReplacementReceipt` and per-original `ReplacementEvidence` belong to the Work Plan owner. Replacement evidence structure MUST retain immutable merge snapshots and append-only consumption events under Project ownership with admission. The original Item, Plan outcomes and PR owner remain independent. Check: `test_exact_edge_release_consumption_and_replay`, PostgreSQL admission/withdrawal/control/recovery barriers and `test_activity_failure_rolls_back_acceptance` in `test_replacements.py`. Decision: `ADR-work-item-replacement-evidence`.

Mutation locks use Project, deterministic Plans, deterministic Runs, deterministic Items, then evidence. Existing admission retains Project → Plan → catalog and commits consumed evidence with its conditional Item lease/admission write; no Run lock is acquired afterward. Project serialization prevents competing evidence/recovery/control owners from interleaving. Check: PostgreSQL barrier tests; acquisition order also receives code review.

Evidence tables reference retained Plan/Item lifetimes and preserve replacement snapshots after detailed Run retirement. Historical requests are actor/path/payload-bound and replay before current revision checks. The HTTP adapter exposes feature-local refusal codes inside the existing detail envelope; the global error handler remains independent. Check: retained/pruning, replay and migration roundtrip integration tests.

## Decision notification maintenance boundary

`DecisionSubscription`, `DecisionNotice`, `DecisionNoticeAttempt`, `DecisionNoticeRequest` and the queue cursor belong to Notifications. Shared maintenance MUST run notification collection after its existing execution owners and bound the notification pass to45 seconds. Each pass rotates at most four channels, scans at most100 persisted discovery entries per channel and admits at most one message per channel. Check: Review only for notification ordering, bound and cursor constants in `decision_worker.py` and maintenance `task.py`; existing maintenance regression tests cover the preceding owners.

Admission MUST serialize through the Notification channel before subscription and attempt state. Network delivery follows durable admission outside the database transaction; outcome persistence checks the exact token, state and60-second lease. Expiry preserves unknown rather than repeating transport. PostgreSQL admission and late-result tests in `modules/hub/tests/integration/features/notifications/test_decision_notices.py` enforce this fence. Per-channel exceptions remain isolated from existing work; a persisted cursor advances fairness across passes. The contract is bounded maintenance work, not a wall-clock delivery guarantee.

The migration freezes its schema definitions. Decision generation tombstones and immutable command receipts survive detailed attempt compaction; deletion of the owning channel cascades notice evidence. Check: `modules/hub/tests/integration/migrations/test_decision_notices.py`. `ADR-decision-notice-delivery` records why polling and retained uncertainty are used.
