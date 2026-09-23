# Work plans

Work plans manage work before a pull request exists. The local implementation is
available in **Project → Plans** and the API below; deployment and a live GitHub
canary are still pending. [Design decisions](work-plans-design.md) record the
agreed domain boundaries and the original proposals.

## Registration and dependencies

Adding a plan requests execution without a second approval. Register 1–100 items,
including their specification and acceptance criteria, in one atomic request.
The form also accepts a JSON task array for bulk input. Plan dependencies select
existing plans in the same project. Item dependencies use keys within that plan.
Cross-plan item references and direct plan/item edges are permanently unsupported.
Self references, cycles, missing targets, and duplicate keys/edges are rejected.
Composite foreign keys enforce project/plan boundaries in the database.

The first release uses one GitHub repository per project and a specified target
branch (`main` by default; change it for repositories using another branch).
Plans can depend on plans, and items can depend on items in their own plan.
All parents must succeed. A successful item requires a confirmed PR merge to
its original target branch; agent completion, passing CI, closed issues, or a
missing run do not satisfy a dependency.

The existing project dispatcher observes runs and then admits eligible work items.
Independent plans/items share the project's and catalog's capacity. A database
transaction fixes the item's start before branch preparation. Preparation reserves
local admission space; the existing catalog gateway still authorizes actual agent
delivery and owns quota accounting. Waiting dependencies hold no execution slot.
Registration, edits, and resume start newly ready items within the same request,
including branch/PR preparation and the first agent dispatch. A webhook for a work
item's run observes that item at once, so a confirmed merge starts its dependents
without waiting for the tick. This follow-up has a 25-second budget and at most two
admissions; anything unfinished, refused, or failed stays due for the scheduler tick,
which remains the recovery path. Pause and revoke never start work.

A deterministic `autohub/work/<item-id>` branch is created from the target head
recorded at admission/preparation. A temporary `.autohub/work-items/<item-id>.md`
file provides the initial PR diff. The implementation request tells the agent to
remove it. PRs are created ready for review, so the project's existing automatic
merge policy can apply without a separate Draft approval. Human Draft changes
remain effective. Manual-merge projects wait for the actual merge.

Local Item specifications become the immutable Run request. GitHub Issue bodies
are not loaded into these requests, including on retries. Work PR target/head
branches are checked again before Hub merges them. Unexpected branch changes
require correction and never release dependencies.

## Controls and recovery

- **Pause** prevents new Item starts. Already admitted preparation and existing
  runs continue, including fixes and merges.
- **Resume** permits waiting items to start after rechecking dependencies and
  capacity; it does not restart existing runs.
- **Revoke** permanently withdraws unstarted items. Started runs continue and
  retain their outcomes. A revoked plan does not satisfy downstream dependencies
  and cannot resume. Completed plans cannot be controlled.
- A paused plan can become completed if all already started items succeed.
- Failed/blocked work holds its dependents; independent work continues.
- Edit a plan's text and dependencies only before any item has started. Item keys
  and membership are fixed; adding/removing work requires another plan. All edits
  and controls require the observed plan revision.

Pause/revoke and Item admission lock the same project and plan. If control wins,
no waiting item starts. If admission wins, that item is already started and may
continue. Item leases fence local result writes and expire for recovery. External
requests have shorter timeouts than their leases, and deterministic branch/PR
identities reconcile lost responses before creating another resource.

The Plans view distinguishes dependency waits, capacity waits, pauses, run
failures, and Issue synchronization delays. Use the linked Runs view for existing
pipeline pause/resume controls; Plan resume never replays an agent request.
Failed/canceled Run retry and PR replacement do not yet have an Item-level API.
A target branch confirmed absent before preparation writes stops in
`preparation_failed` and releases its reserved execution capacity. A ref lookup's
404 alone is insufficient: a successful matching-ref listing must also lack the
exact branch. An unavailable listing remains retryable, as do raw HTTP errors
during later preparation or reconciliation. The failure is retained and dependents
stay waiting. Plan resume does not retry a confirmed missing base; register replacement
work with corrected settings. Authentication failures, temporary creation restrictions
(including 422), server errors, and uncertain responses continue reconciliation with
the reservation held. A 422 carrying a rate-limit header preserves its retry delay.
Retries retain their branch/PR identity and cannot blindly recreate a PR.
Changing a project's repository/connector does not retarget existing plans;
restore the original binding or register new work in the intended project.

## GitHub Issues are outbound records only

The shared maintenance worker publishes a parent Issue for each Plan and a
sub-issue for each Item. It copies the local specification, acceptance criteria,
status history, dependency references, and PR/merge links. Dependencies are shown
as body links in this release, not synchronized native blocking relationships.
The body retains the last 100 observed state transitions; it is not a polling log.

The Issue body identifies it as an AutoHub-managed record. Remote edits, comments,
closing/reopening, and relationship changes never change execution or completion.
They may be overwritten on the next local update. Work execution does not wait
for Issue creation, parent linking, or updates; synchronization failures have
separate visible error/pending fields and a retry time.

An outbound snapshot is stored transactionally with each local control/result.
A lease and digest protect concurrent publication. Each maintenance pass publishes
at most four records sequentially with a one-second gap and a five-minute retry
cooldown (or GitHub's rate-limit delay). The same GitHub connector needs Issues
write permission in addition to the existing contents/PR permissions. Missing
Issues permissions do not prevent PR execution.

Creation intent is persisted before posting. A lost response is reconciled using
the exact entity marker and authenticated author, scanning at most 1,000 issues.
Failures during this lookup preserve the uncertain creation intent; only a definitive
rejection of the creation request permits a fresh POST.
If creation remains uncertain and no matching Issue is found, Hub reports that
condition and continues reconciliation without posting another Issue. This also
covers a crash between committing intent and sending the request. There is not
yet a manual resolution API for this ambiguous case. Known Issue deletion or a
changed connector identity can likewise require operator investigation; these
record problems never mark an Item successful or stop work.

## History retention

Plan/Item specifications, edges, and final results have no automatic expiry.
Successful Items retain their completion timestamp, repository/target (on Plan),
PR number/URL, merge SHA, and execution ID when their detailed Run is removed.
The Run link is nulled and `pipeline_run_retired_at` records normal expiry.

An attached Run is protected unless its Item has explicit successful merge
evidence and that completion is at least 30 days old. The existing Run last-update
30-day threshold and active-lease protection also apply. Unresolved failures,
blocked/paused runs, and missing success evidence cannot be pruned. Independent
Run retention and Jules session non-readoption markers retain their prior behavior.
This release conservatively keeps failed/canceled Item runs even after Plan revoke;
revoke withdraws unstarted work, not the investigation of a started failure.

The pruner locks Runs before updating Item links; result observation uses the same
order. Completion evidence is committed before any referenced Run becomes eligible
for deletion. An unexpected missing Run produces an attention state, never success.

## API

All routes require the same signed-in user authorization as project management.
Base path: `/api/v1/projects/{project_id}/work-plans`.

| Method and suffix | Operation |
| --- | --- |
| `GET /` | List plans with their items and Issue sync status; `offset`, `limit` (1–100). |
| `POST /` | Atomically register a plan and its Item graph. |
| `GET /{plan_id}` | Read local state; no external writes. |
| `PUT /{plan_id}` | Edit unstarted work, including dependency graphs; requires `expected_revision`. |
| `POST /{plan_id}/control` | `action`: `pause`, `resume`, or `revoke`; requires `expected_revision`. |

Creation fields: `title`, optional `description`, `base_branch`, `depends_on`
(existing Plan UUIDs), and `items`. Each Item requires a stable `key`, `title`,
`description`, `acceptance`, and optional `depends_on` (local Item keys).
The generated OpenAPI client is the definitive request/response contract.

## Deployment and validation

Apply migration `c7d8e9f0a1b2` with the matching application version. It adds five
work tables and does not alter existing tables. Keep the project dispatcher and
shared maintenance worker enabled. No per-Plan schedules are created.

Automated coverage includes graph validation, controls, capacity, PR response-loss
recovery, manual-merge observation, outbound Issue failures and response loss,
retained completion evidence, unexpected missing runs, PostgreSQL concurrent
admission, migration upgrade/downgrade, and frontend registration/control behavior.
A live canary should verify creation of a two-item dependent plan, its PR workflow,
Issue permissions/sub-issue links, pause/revoke, and post-merge release in a target
repository. Automated tests use stubbed GitHub I/O; no live plan is created by them.
