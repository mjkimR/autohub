# Work plans

Work plans manage work before a pull request exists. They are available in
**Project → Plans** and the API below, deployed, and verified by live GitHub
canaries. The registration identity and MCP additions dated 2026-09-30 are local
and not yet deployed. One-time start reservations added on 2026-10-01 are also
local and not yet deployed. Draft/proposed plans and activity history added on
2026-10-01 are local and not yet deployed. [Design decisions](work-plans-design.md) record the
agreed domain boundaries and the original proposals.

## Registration and dependencies

Adding an `active` plan (the API default) requests execution without a second
approval. Register 1–100 complete items in one atomic request. Set `state=draft`
to save a seed with zero or incomplete items; `proposed` submits complete work for
a decision, and `paused` stores validated work on hold. None of these three states
admits work. The UI defaults to Draft. See [backlog and activity](work-plan-backlog.md)
for the lifecycle, editing rules and discussion contract.
The form also accepts a JSON task array for bulk input. Plan dependencies select
existing plans in the same project. Item dependencies use keys within that plan.
Cross-plan item references and direct plan/item edges are permanently unsupported.
Self references, cycles, missing targets, and duplicate keys/edges are rejected.
Composite foreign keys enforce project/plan boundaries in the database.

Set optional `scheduled_at` to reserve a one-time earliest start for the whole
plan. Omit it or use `null` for immediate eligibility. REST and MCP require a
timezone offset or `Z`; Hub normalizes the instant to UTC. The form accepts and
displays the browser's local time zone. A past time is already eligible. Before
the reserved time, no item is admitted and no execution capacity is reserved;
registration, edits, resume, and webhook follow-up all honor this condition.
At or after that time, the existing dispatcher admits work when dependencies,
project/catalog availability, and capacity allow it. This is not an exact-time
guarantee: the production external tick currently runs every five minutes, and
outages or other holds can delay execution further. Overdue work remains eligible
after recovery. There are no per-plan timers or recurring plan schedules.

Change or clear the reservation through the normal revision-checked edit while
all items are unstarted. Clearing it can start eligible work immediately. Pause
continues to hold overdue work, resume still respects a future reservation, and
revoke permanently withdraws unstarted work. Already started work continues.

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
Active registration, active edits, and resume start newly ready items within the same request,
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

## Registration identity and MCP

New UI registrations send a UUID `request_id`; MCP `work_plans_register` requires
it. REST `POST` accepts it optionally to preserve older clients. Callers that omit
it do not get registration deduplication. Generate the ID before issuing the
request and retain it across retries.

A unique constraint on `(project_id, registration_request_id)` and the project
lock serialize concurrent registrations. The normalized digest includes defaults,
text, branch, specifications and dependencies; item/dependency ordering does not
change it. Same key and content returns the existing Plan's current state, even
if it has since paused or progressed. Different content with the same key returns
409 and never edits the existing Plan. A different key creates different work;
Hub does not detect semantic duplicates.

Recover a lost response with `GET /registrations/{request_id}` or MCP
`work_plans_get` with `project_id` and `request_id`. The key lives as long as the
Plan. After a saved Plan's immediate kick fails, retrieve that Plan and let the
existing scheduler recover; do not mint another key. The UI retains its key while
the form remains mounted. If the form was closed/reloaded after an uncertain
response, inspect existing Plans before submitting anew.

Work MCP exposes `work_plans_list`, `work_plans_get` (read scope), and
`work_plans_register`, `work_plans_update`, `work_plans_set_group`, `work_plans_control` (write scope). Activity adds `work_plans_activity` (read) and `work_plans_comment` (write).
These reuse the same services, validation and admission paths as REST. Operations
scope is not required. [MCP contracts](mcp.md) describe the nested inputs.

## Group classification

`WorkPlan.group_key` is optional, project-local classification metadata (up to 100
characters, case-sensitive). Leading/trailing whitespace is removed; empty values
become SQL/JSON `null`. Existing plans remain ungrouped. The UI displays this as
`(null)` and distinguishes it from All groups and a literal string key.

Groups do not restrict code paths, dependencies, permissions, execution capacity,
or merge policy. A Plan may span several games/modules with or without a key;
`null` means unclassified, not membership in every group. Filtering a group does
not find every task that can affect that group's code.

Plan lists and Run lists support `group_key`: omit it (or pass MCP `null`) for all
groups, pass an empty string for ungrouped work, or a nonempty string for an exact
match after trimming. Filtering precedes pagination/counts and combines with
existing project/state filters. Runs inherit classification through their Work
Item's Plan, so reclassification affects their next list query. Directly enrolled
Runs without a Plan also appear in the ungrouped view. No key is copied to Items,
Runs, or execution request snapshots.

Use `PATCH /{plan_id}/group` with `group_key`, `expected_revision`, and optional
`reason` to change/clear classification in any lifecycle state. This only changes
metadata, revision and activity history; it does not kick execution or withdraw a
proposal. A stale revision returns 409. Normal unstarted-plan edits also accept
`group_key`; omitting it preserves the current value, while explicit null clears it.

The group editor stays open when list filters change and retains unsaved input.
After a revision conflict, Refresh loads the current saved group without replacing
that input or submitting it. Review the displayed group and explicitly save again;
the retry uses the refreshed Plan revision. Cancel remains available even when
the edited Plan is outside the current list filter.

The key is excluded from the registration digest. Retrying a registration returns
the existing Plan with its current group, even if the retry supplies a different
key; retries never reclassify existing work. Specification changes still conflict.
Use the explicit group update to change classification. Group-wide bulk controls,
persistent holds and isolation policies are outside this feature.

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
- Edit a plan's text and dependencies only before any item has started. Draft/proposed
  plans permit item additions/removals; editing proposed work returns it to draft.
  Active/paused plans retain fixed membership. All edits and controls require the
  observed revision; an optional `reason` is stored in activity history.
- `propose` validates and submits a draft for review; `draft` withdraws a proposal.
  `ready` validates draft/proposed work and holds it paused. `resume` explicitly
  authorizes execution from draft/proposed/paused after full validation. Incomplete
  work cannot leave draft. `pause` cannot bypass draft/proposal validation.
  Published plans cannot return to draft; started Runs retain their existing controls.

Pause/revoke and Item admission lock the same project and plan. If control wins,
no waiting item starts. If admission wins, that item is already started and may
continue. Item leases fence local result writes and expire for recovery. External
requests have shorter timeouts than their leases, and deterministic branch/PR
identities reconcile lost responses before creating another resource.

The Plans view distinguishes dependency waits, capacity waits, pauses, run
failures, and Issue synchronization delays. Use the linked Runs view for existing
pipeline pause/resume controls; Plan resume never replays an agent request.
Failed/canceled Run retry and PR replacement do not have an Item-level API.
[Run decisions and recovery](run-decisions.md#replacing-failed-work) gives the
replacement inventory, explicit links and dependent-work rebuilding procedure.
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

Draft/proposed plans stay local and create no Issue records. Revoking one before
publication also creates none. Once ready or active, the shared maintenance worker
publishes a parent Issue for each Plan and a
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
cooldown (or GitHub's rate-limit delay). A webhook for an active run also runs one
such pass after its follow-up, within a 20-second budget, so a plan's Issues appear
once its first PR opens and close on the merge that completes them; maintenance
retries whatever that pass leaves. The same GitHub connector needs Issues
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
| `GET /` | List plans with their items and Issue sync status; `offset`, `limit` (1–100), optional `state` and `group_key`. |
| `POST /` | Atomically register a plan and its Item graph. |
| `GET /registrations/{request_id}` | Recover a registration without creating work. |
| `GET /{plan_id}` | Read local state; no external writes. |
| `PUT /{plan_id}` | Edit unstarted work, including dependency graphs; requires `expected_revision`. |
| `PATCH /{plan_id}/group` | Reclassify any Plan without execution; requires `group_key` and `expected_revision`. |
| `POST /{plan_id}/control` | `action`: `propose`, `draft`, `ready`, `pause`, `resume`, or `revoke`; requires `expected_revision`. |
| `GET /{plan_id}/activity` | Append-only changes/comments, `offset`, `limit`, optional `comments_only`. |
| `POST /{plan_id}/comments` | Bounded text `body` and client UUID `request_id`; retries are idempotent per Plan. |

Creation fields: optional `state` (`active` default, `draft`, `proposed`, `paused`), optional `request_id` (required for reliable retries), `title`, optional `group_key`, `description`, `base_branch`, `depends_on`
(existing Plan UUIDs), optional `scheduled_at` (timezone-aware earliest start), and `items`. Draft items require a stable `key`; title, description and acceptance
can be filled later. All other initial states require 1–100 complete items.
`depends_on` contains local Item keys and is validated even in drafts.
The generated OpenAPI client is the definitive request/response contract.

## Deployment and validation

The original migration `c7d8e9f0a1b2` added five work tables. Current deployment
must apply the full migration head, including `e14a217d0910` (Run decisions),
`f25b328e1021` (Plan registration identity), `a36c439f2132` (Plan start reservation),
`b47d540a3243` (Plan activity), and `c58e651b4354` (Plan group classification), with the matching application/UI. Keep the project dispatcher and
shared maintenance worker enabled. No per-Plan schedules are created.

Automated coverage includes graph validation, controls, capacity, PR response-loss
recovery, manual-merge observation, outbound Issue failures and response loss,
retained completion evidence, unexpected missing runs, PostgreSQL concurrent
admission, migration upgrade/downgrade, and frontend registration/control behavior.
The [2026-09-23 canary](canary-results-2026-09-23.md) verified a two-item dependent
plan, its PR workflow, Issue permissions/sub-issue links, pause/revoke, and immediate
post-merge release in a target repository. The [2026-09-28 canary](canary-results-2026-09-28.md)
verified Issue creation and closure within seconds of webhook processing; synchronization
publishes a plan whose Issue does not exist yet before its items so they can link to it.
Automated tests use stubbed GitHub I/O; no live plan is created by them.
