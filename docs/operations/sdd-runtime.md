# Operate repository-owned SDD activities

`CAP-SDD-native-delivery` owns explicit Planning/Development intent over ordinary
PR delivery. The repository and its working agent own setup, asset management and
internal workflow. Hub does not install devkit, run or delegate `devkit sync`,
probe a repository runtime or evaluate its readiness.

## Serving host

Use the ordinary backend deployment and matching database migration. No SDD
runtime profile, source-read token, runtime cache, pinned build environment,
mounted repository checkout or bubblewrap probe is required. Remove obsolete
`AUTOHUB_SDD_*` variables and `AUTOHUB_FLOW_DELIVERY_TARGETS` from serving
configuration. Auto Hub's contributor devkit setup remains separate.

## Start and follow work

1. Enable the project and its GitHub/catalog connection.
2. Select the repository unit, base and Planning/Development intent. Status and
   size are descriptive; the working agent decides how to handle repository rules.
3. Start the activity and retain its request identity. Both activity kinds create
   a Draft PR through GitHub APIs; Hub does not author a proposal-state commit.
4. Follow the ordinary Run and its agent question/answer/explicit-resume path.
5. Mark the PR ready in GitHub when it may merge. Hub observes the configured
   current-head checks and project merge policy.

If repository verification is needed, its owner configures GitHub Actions. This
procedure introduces no Action or runner for readiness or asset restoration.
A missing setup or internal gate can be reported after the agent starts.

## Uncertain activity publication

Keep the original repository/unit/base/activity/preferences and request UUID after
a lost response. Check or retry that exact request. A new intent is not a safe
substitute for resolving the original branch/PR candidate. An ownership conflict
identifies the owner or retained evidence that must be inspected first.

## Retired execution and claim reconciliation

Legacy native Runs, typed decisions, executable milestone previews and automatic
native batches cannot resume. Retained tombstones return `SDD_EXECUTION_RETIRED`;
stored Run/decision/batch/claim evidence remains read-only. Local batch Stop, where
exposed, only settles future admission and does not cancel external agent work.

Inspect a retained claim with:

```sh
curl -s "$SERVICE_URL/api/v1/projects/<project-id>/sdd/claims/<claim-id>"
```

After inspecting the exact saved candidate, linked Run/PR and any externally
posted work, explicitly reconcile the selected retired claim or eligible uncertain
no-Run publication with its returned
checkpoint digest, a stable request UUID and `acknowledge_external_work: true`.
The endpoint is `POST /api/v1/projects/<project-id>/sdd/claims/<claim-id>/reconcile`.
This acknowledgment releases only that reservation and acknowledges its exact
linked terminal retired Run. It neither resumes the old Run nor creates another
activity or merge authority. A current optimistic publication is eligible only if it is uncertain, has no
bound Run and no live lease. Local release does not remove/adopt its remote branch;
an existing candidate remains a conflict for a distinct new start. A changed
checkpoint needs fresh inspection; an uncertain provider effect must not be described as canceled.

A terminal retired Run without a claim can be acknowledged through
`POST /api/v1/projects/<project-id>/sdd/runs/<run-id>/reconcile` with a stable
`request_id`, its inspected `expected_revision` and
`acknowledge_external_work: true`. The Run stays terminal; the recorded receipt
clears only its unreconciled-external-work hold. An independently retained
unsettled claim still needs its own exact claim reconciliation; Run acknowledgment
alone does not release that reservation. An identical replay returns its retained
outcome, while a changed request identity conflicts.

## Rollout and rollback

1. Stop accepting legacy-native work before deploying the matching backend/UI and
   retirement migration.
2. Inspect active provider work and saved native publication candidates. Local
   migration cancellation cannot stop work already dispatched to a provider.
3. Apply the migration. It cancels nonterminal old native Runs, revokes local
   leases, stops legacy batches and preserves snapshots, attempts and exact claims.
4. Confirm ordinary activity starts, retained history and explicit claim
   reconciliation on the intended service revision.
5. Register replacement work only after inspecting and acknowledging uncertain
   old ownership. Never treat a canceled local Run as proof of remote absence.

A downgrade does not reactivate retired Runs, batches or claims. Settled history
is not converted into an optimistic Run.

## SDK bridge retirement

`autohub.sdd:*` and `autohub.pr_delivery:*` built-in bindings are retired under
`CAP-SDK-existing-pr-bridge`. New effects return `SDD_BRIDGE_RETIRED`.
Unreceipted old work settles terminally; an exact receipt-backed delivery can
observe its existing PR owner without repeating resume. Completed results remain
readable. Configure generic HTTP SDK workers through
[execution targets](execution-targets.md) when that independent protocol is needed.

## Live canary after deployment

Use an explicitly approved test repository/PR. Check an optimistic Draft activity
start, a correlated agent question, saved answer plus explicit resume, and the
operator's GitHub ready decision followed by current-head CI/merge observation.
Record service/source identity and exact Run/PR links in
[delivery status](deployment-status.md). Local fixtures do not establish live
provider or GitHub behavior.
