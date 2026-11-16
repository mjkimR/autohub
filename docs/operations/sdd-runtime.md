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

## Inspect and reconcile uncertain publication

Inspect the claim at `GET /api/v1/projects/<project-id>/sdd/claims/<claim-id>`.
After inspecting the exact saved branch/PR and external agent work, acknowledge the
reservation at `POST /api/v1/projects/<project-id>/sdd/claims/<claim-id>/reconcile`.
Supply the returned checkpoint digest, a stable request UUID and
`acknowledge_external_work: true`. The claim is eligible only when publication is
uncertain, no Run is bound and no live lease remains. A changed checkpoint requires
fresh inspection. Replaying the identical acknowledgment returns its recorded result.

Release preserves remote artifacts. It neither stops an agent nor resumes a Run.
An existing candidate branch remains a conflict for a distinct start.

## Schema update

Deploy matching backend and UI artifacts and apply the database migrations. The
cleanup migration removes unused native batch tables, the claim member link and
SDK PR bridge links. Current activity claims and generic task-flow records remain.
There is no legacy native work to migrate or acknowledge.

## Live canary after deployment

Use an explicitly approved test repository/PR. Check an optimistic Draft activity
start, a correlated agent question, saved answer plus explicit resume, and the
operator's GitHub ready decision followed by current-head CI/merge observation.
Record service/source identity and exact Run/PR links in
[delivery status](deployment-status.md). Local fixtures do not establish live
provider or GitHub behavior.
