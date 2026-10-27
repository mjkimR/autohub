# Run decisions and recovery

Status: implemented locally on 2026-09-30; not deployed or verified with a live
provider. These controls use the existing Run, attempt, delivery and scheduler.
They do not add a planning chat service or another execution engine.

## Control contract

| Action | Effect |
| --- | --- |
| Plan pause | Stops admission of unstarted items; admitted work and Runs continue. |
| Run pause | Stops Hub progression and invalidates its observation lease. Already sent provider work can continue. |
| Ask | Persists a question against the current PR head and last attempt, then blocks Hub progression. |
| Answer | Appends a response and increments the Run revision; does not resume or deliver work. |
| Resume with answer | Rechecks the Run, project binding and PR; fixes the chosen response into a new attempt and its durable delivery. |
| Dismiss question | Records an explicit reason and leaves the Run stopped. |
| Cancel Run | Ends Hub execution; does not prove that remote work stopped. |

Only paused/blocked Runs can resume. Failed/canceled/completed Runs cannot. A
resume of an externally implemented PR without a decision returns to CI
observation, as does one whose PR head changed after the last delivered request
(e.g. the agent pushed while paused); otherwise resume re-sends that request. Applying an answer explicitly requests implementation work even for
that PR. Plan resume never retries an existing Run.

Controls share the Run lock and revision/lease fencing with result observation.
If pause, cancellation or approval revocation wins before the final merge
authorization check (including during its GitHub read), the stale continuation
is rejected. Once an external request has been authorized and sent, pause cannot
recall it. Inspect the provider conversation and current PR before requesting
another attempt; no provider cancellation acknowledgement is implied.

## User workflow

Open **Runs → Decisions**, inspect the PR and pause reason, then save an answer.
The Run stays blocked. **Resume with this answer** selects a particular response;
later answers never overwrite earlier records. After resuming, use attempt history
to inspect delivery state, provider replies and failures. An applied answer means
the attempt was prepared, not that delivery or implementation succeeded.

The dialog also records operator questions, displays past questions and responses,
and dismisses stale questions with a reason. The main column shows the current
wait, pending question and next action; the history column moves below it on small
screens. Approval activity initially shows five entries, with up to 100 available
on expansion. Change requests, dismissal, recovery and stop/revoke controls reveal
their inputs when selected. A pending question disables integration decisions;
mutations share a busy state while saving and refreshing the inspected evidence.
Use the existing blocked/paused Run
filters for the waiting list. The first release permits one pending question per
Run. It does not provide cross-project grouping, a conversation inbox, or batch
controls. Existing operator notices report state changes; there is no separate
answer notification channel.

If the PR head changed since the question, resume returns a conflict. Read the
current PR, dismiss the stale question, and record a new question/answer if still
needed. Dismissal alone never resumes. Answers clarify the original specification;
changed scope or acceptance criteria require separately reviewed replacement work.
The original request snapshot stays immutable, and subsequent CI/conflict fixes
inherit the clarified instructions.

## REST and MCP

REST base: `/api/v1/pipeline-runs/{run_id}`. Existing signed-in user authorization
applies. The work MCP endpoint uses read/write scopes and records the authenticated
machine as actor; callers cannot supply another actor.

| REST | MCP | Input |
| --- | --- | --- |
| `GET /questions` | `runs_questions` | `offset`, `limit`; returns questions, answers, total and current `run_revision`. |
| `POST /questions` | `runs_ask` | `request_id`, `expected_revision`, `question`; MCP nests these under `question`. |
| `POST /questions/{question_id}/answers` | `runs_answer` | `request_id`, `expected_revision`, `answer`; MCP nests these under `response`. |
| `POST /questions/{question_id}/dismiss` | `runs_dismiss_question` | `expected_revision`, `reason`; MCP nests these under `resolution`. |
| `POST /resume` | `runs_resume` | Required `request_id`, `expected_revision`; optional `answer_id`. |

Each MCP call also takes `run_id`, and answer/dismiss take `question_id`.
Example sequence, after reading the latest revision:

```json
{"tool":"runs_answer","arguments":{"run_id":"RUN_UUID","question_id":"QUESTION_UUID","response":{"request_id":"ANSWER_REQUEST_UUID","expected_revision":12,"answer":"Keep the existing empty state."}}}
```

Read `runs_get` again, inspect any changes, then use the returned answer ID and
current revision in `runs_resume`. Do not assume the next revision is exactly +1.

Generate a UUID once per intended ask, answer or resume. Retry the same request
with the same ID and actor after response loss. Ask/answer reuse checks the target,
text and actor before revision validation; a changed expected revision alone does
not create another record. Resume receipts check the entire input, including
revision, actor and selected answer. A different payload under a used resume ID
conflicts. Successful replays return current state, never replay the transition:
an old successful resume cannot undo a later pause. Dismiss is revision guarded;
read history after a lost response before retrying it.

Resume records the receipt, answer application, new attempt and delivery in one
transaction. Quota waits and uncertain delivery use existing delivery recovery;
they do not require another answer or another resume. Request IDs are not a global
deduplication mechanism across clients: a new ID expresses a new request.
The UI preserves IDs while a dialog remains open. After closing/reloading during
an uncertain response, inspect history/current state before submitting again.
Refreshing within the dialog preserves an uncertain answer's request ID across
revision changes. Acknowledgement ends that submission's retry identity. Controls
require successful Run and question reads with matching revisions; a failed or
inconsistent refresh leaves history visible but disables mutations until reloaded.

## Agent question protocol

The Codex PR mention prompt asks the agent to stop before pushing and include one
single-line JSON marker in its PR reply:

```html
<!-- autohub-question {"attempt":"hub-attempt:ATTEMPT_KEY","head":"EXACT_HEAD_SHA","question":"Which empty state should be used?"} -->
```

The existing reply collector authenticates the author as
`chatgpt-codex-connector`; Hub also matches the current attempt correlation marker
and delivered head. Event IDs become deterministic question IDs. Arbitrary
authors, mismatched attempts/heads, malformed or oversized markers, nested HTML
comments and executable mention text are not turned into questions. Collected
stale replies remain in attempt history but cannot stop a new attempt. This is
currently the Codex PR reply path only; Jules session questions are not supported.
For general runs, if the agent pushes before asking, the head-change path enters
CI observation and the marker is not collected as a decision. Native SDD runs
continue collecting replies after a push, validate the marker against the delivered
attempt/head, and bind the question to the currently observed head. An operator
can also record a question through the UI/MCP.

Question text is limited to 8,000 decoded characters. The reply scan is bounded at
112,000 characters to allow JSON Unicode escapes (up to 12 characters per code
point), marker metadata and surrounding prose without reducing the text limit.

Live verification must confirm that the provider actually emits this marker as a
trusted PR reply, stops before pushing, and uses the selected answer in its next
implementation. Passing parser and mocked GitHub tests does not establish this.

## Native SDD decisions

Enrolling a pull request with a spec is the explicit attach of the cloud path: the
pull request's head must be the unit's activity branch, `dev-<slug>` for
`specs/YYYY-MM/YYYYMMDD-<slug>`, the same rule the local Host applies; readiness
and enrollment refuse another head. Native runs use the same questions, answers,
Run lock and resume receipts. Applied
questions and their selected answers, plus explicit change requests, are included
in subsequent stage requests in chronological order. Unapplied answers are not
execution instructions. CI/conflict fixes inherit the stage request snapshot.

Answering a question is a clarification, not an approval or an assertion that code
must change. A no-change answer can return to the existing `dev-integration` gate
without a new commit. Request changes explicitly requires a changed head and renewed workflow
evidence. If changes do not arrive within 45 minutes, the run blocks; resume retries
the work with its recorded context and does not erase the outstanding requirement.

At the `dev-integration` gate, after CLI evidence is ready, either an observed ready
PR or **Approve integration** records authorization in Hub and passes it to devkit as
`--given dev-integration`; the gate's answer channel is `given`, so no decision record
is written for it. Policy `dev-integration=auto` can also authorize integration. Ready observations are attributed to `github:pr-ready`, not a guessed
human actor; the receipt stores the observation time, head, base and evidence digest.
Draft `dev-integration` waits are paused and hold no execution slot. The scheduler checks them
every five minutes, subject to its tick; manual pause and pending questions are
never auto-resumed. Older paused native runs without the wait marker need one
explicit resume to refresh their inspection and enable this polling.

Hub approval does not change GitHub draft status: integration can proceed while
draft, but the operator must mark the PR ready before merging. `auto_merge=false`
still disables automatic merging. Returning an observed ready PR to draft revokes
its authorization. Explicit revocation, rework and answers at/after `dev-integration` withhold automatic
approval: an existing ready flag or auto policy cannot undo the decision, even after
a generic resume. Worker questions (`question:*` requests) are not Hub decisions:
they are answered with an answer envelope on the pull request. Review the resulting evidence and explicitly approve in Hub.
Earlier implementation clarifications retain the configured integration policy.

Worker envelopes hold a run (devkit's envelope contract, section 4). An unresolved
`problem` or a malformed worker envelope blocks the run with the problem's cause and
recovery in the pause reason and in the next agent request; only a `resolution`
envelope written by whoever fixed it clears the hold, so resume re-inspects and does
not grant anything. An unanswered worker question appears as a `question:*` request:
the operator chooses an option, or writes a decision outside them, and Hub records
the answer as an `answer-envelope` decision record that the agent writes with
`devkit workflow envelope answer` on the pull request. Questions are never declined
or deferred. While a problem or question stands, no gate passes, approval is refused
and nothing is merged. `activity_effort` (`low`, `medium`, `high`) is a run option of
sdd enrollment: it is recorded in the run's snapshot, passed to the agent with every
request and reported back by the worker envelope.

The Repository spec view lists its latest 20 related executions, joined through
recorded handoffs within the project, and links directly to their Decisions dialog.
The dialog displays current evidence, final-report and support/review rounds at
the inspected commit, draft/approval requirements and the
latest 100 approval, rework, revocation and resume records. Questions and selected
answers remain in the existing question history. These native changes are locally
tested; deployment and a live provider canary remain separate.

## Starting Planning and Development

`POST /projects/{id}/sdd/proposals/{slug}/planning` (MCP `sdd_start_planning`)
starts Planning of a draft proposal that has `plan-intent` recorded or delegated and does not
need decomposition: Hub creates `plan-<slug>` from `base_branch` with one start
commit that sets `status: reviewing`, opens a ready pull request and enrolls the run.
Its first attempt is the Planning worker, which leaves one worker envelope per run;
the run asks for `plan-accept` only after a completed worker envelope.
`POST /projects/{id}/sdd/proposals/{slug}/development` (MCP `sdd_start_development`)
starts Development of an accepted proposal: `dev-<slug>` with an empty start commit,
a draft pull request and a handoff-first run. Its first step is
`devkit spec proposal handoff <slug>`; once the proposal unit is gone, the run follows
the new spec bundle and its workflow from the next stage, keeping the activity effort.
Both refuse an existing remote branch of that name unless it carries Hub's own open
pull request (a start whose response was lost, enrolled again). Branches that were
never pushed are the local Host's to check before it calls. Both take
`activity_effort` and `catalog`.

## Proposals panel

The repository view of an sdd project lists the proposals of a base branch
(`GET /projects/{id}/sdd/proposals?base_branch=main`, at most 50). Each row shows the
base status and a display status: a draft with a remote `plan-<slug>` shows as
`reviewing` without any base commit. It links the open `plan-` and `dev-` pull
requests and the proposal's unfinished run, and offers only the actions its state
allows: **Start review** for a draft that needs no decomposition and has no Planning
branch, **Review & accept** and **Reject…** (reason required) while its run waits at
`gate:plan-accept`, unheld, and **Start development** for an accepted proposal
without a Development branch. A rejected proposal offers nothing and reads as
waiting for the hygiene cleanup of a local Host. The start buttons send the chosen
base branch and an optional effort override; otherwise the proposal recommendation applies.

## Proposal decisions

A proposal run (unit `docs/proposals/PROP-<slug>` on branch `plan-<slug>`) stops at
`gate:plan-accept` while the proposal is `reviewing`. The person decides with
`decision: accept_plan` or `reject_plan` on `POST /pipeline-runs/{id}/resume` (MCP
`runs_resume`), always with `head_sha`, the pull request head they inspected; a
rejection needs `feedback`, the reason. Hub refuses another head, changed evidence,
a run that is not waiting, a held unit (acceptance) and a proposal that is not
`reviewing`. It then writes the decision itself, without an agent: in a disposable
checkout of that head on `plan-<slug>`, `devkit spec proposal accept <slug> --by user`
validates Planning ownership and records both `gate:plan-accept` and `status: accepted`
in one operation. The note retains the Hub request ID and actual user actor; the
CLI's `user` value identifies decision authority, while the commit and run retain
the decider's identity. For rejection, Hub sets `status: rejected` only and devkit
closes every open worker question with an answer envelope whose choice is null and
whose decision names the rejection (rejection). Git commits inside the sandbox as the
Hub identity (`AUTOHUB_SDD_COMMIT_IDENTITY`, default
`AutoHub <autohub@users.noreply.github.com>`) with a `Decided-by` trailer, and the
push, outside the sandbox with the connector token, holds a lease on the confirmed
head, so a branch that moved meanwhile refuses the commit. The run records the
commit and moves to `awaiting_ci`; the project's CI and merge policy merge the
Planning branch, and the merge commit reuses the decision's message so a squash
keeps the rejection reason where hygiene looks for it. A proposal with an unresolved
worker problem is not accepted; a rejected one is never enrolled or asked again. The
`gate:plan-accept` request cannot be answered as a workflow answer.

Proposal publication first commits a durable intent in the existing resume receipt.
It records the exact candidate commit and inspected evidence before pushing. The
bounded push holds the Run and Project row locks and rechecks their revisions,
binding, enabled state and, for automatic decisions, the advancement lease. A
cancel or project change that wins this fence prevents publication. A stop after
publication preserves its audit record. A lost push/DB response leaves an uncertain
intent; retry the identical saved request with the same actor and request ID.
**Reconcile decision** in approval history does this for a manual decision. An
exact match between the remote head and a prepared candidate confirms publication
without another push. Recovery never renews approval on a canceled or changed run.
For an automatic decision whose push succeeded but result storage failed, generic
resume reconciles the prepared commit before dispatching more work. The error
transition records its own recovery revision atomically; a user action cannot
extend that revision. Recovery still requires the original PR branch/base, project
binding and authorization, and never dispatches another agent or republishes the
decision just to recover its result.
If the remote has moved beyond that candidate, inspect the repository and settle
the old run before enrolling again; recovery does not infer success from ancestry.
No database migration is needed for these receipt fields.

`plan-intent=auto` is recognized through the CLI's completed intent stage rather
than a decision filename. With `plan-accept=auto`, Hub requires delegation from
both the owning base commit and the proposal's pinned policy, a completed current
Planning worker and no worker hold. This applies only on the proposal's Planning
branch, never to a Development activity waiting for its initial handoff. It records
policy authority and uses canonical
`spec proposal accept --by policy`. If the agent already accepted canonically,
Hub writes an audit commit without duplicating the gate. A new push starts fresh
CI observation; draft PRs still wait. Withdrawing approval keeps merge blocked
until explicit reapproval; inspection alone cannot restore it.
For a completed Planning activity whose automatic delegation was withdrawn,
Decisions shows **Approve proposal**. That explicit, revision-checked Hub approval
restores delegation; **Resume after inspection** keeps it withdrawn. Retrying
unfinished requested changes still dispatches work without granting approval.
A queued Run can also withdraw approval before its first Attempt. Generic resume
re-inspects native gates without requiring an implementation Attempt; explicit
reapproval can then continue automatic Planning acceptance without dispatching
unnecessary agent work.

Proposal decisions also respect open or answered-but-unapplied Hub questions,
in addition to the repository's worker-envelope hold. Apply the saved answer or
dismiss the question before accepting or rejecting. Trusted agent questions are
persisted before automatic acceptance is considered. The publication fence checks
questions and withdrawal again immediately before pushing, and recovery cannot
grant approval while a Hub question awaits application. Policy recovery also
preserves withdrawn delegation.

The first observation after publication allows only the decision commit recorded
in the receipt and approval, following its inspected parent. Another head change
still revokes approval. CI must cover the new decision head; a successful run for
the pre-decision commit cannot authorize its merge.

The proposal list opens **Review & accept** in Decisions. Planning evidence appears
before the decision controls: the proposal's effort recommendations, actual worker
effort, all challenger/scout rounds, their closing reverifies, findings, assumptions
and unverified areas. Missing support roles are review guidance, scoped to the
current workflow segment; they do not introduce another workflow engine. Activity
starts use the proposal's `planning_effort` or `dev_effort` hint unless explicitly
overridden. **Next action** explains the current wait or CLI next skill, and
approval history distinguishes publication intent from confirmed approval.

## Replacing failed work

1. Read the failed/canceled Run, PR and provider conversation. Ensure remote work
   is settled and decide whether its partial implementation should be kept.
2. Inventory the original Plan's started, successful, failed and waiting items,
   and downstream Plans. Keep the original failure and merge evidence intact.
3. Pause affected Plans while deciding; pause any ongoing Runs separately if
   needed. Revoke a Plan only when all its remaining unstarted work should be
   withdrawn. Revoke does not cancel already started Runs.
4. Register replacement work with a new request ID. Put the original Plan/Item,
   Run and PR URLs in its description and explain what replaces what. List only
   the failed work and remaining required work; do not recreate successful or
   unrelated running items. This relationship is descriptive, not a successor API.
   A failed item's activity branch (`dev-<key>`) usually still exists: give the
   replacement item `attach_branch` naming it, or a new key; a new start on an
   existing branch is refused.
5. Rebuild dependencies in the replacement Plan, and recreate affected unstarted
   downstream Plans if necessary. Do not depend on the old failed/revoked Plan
   expecting it to become successful. Record old→new Plan/Item mappings in the
   recovery record. Original started specifications remain immutable.
6. Observe actual merges for the replacement graph. The old failure/dependents
   never become successful merely because the replacement completed.

Registration requests execution immediately. Preparing the replacement inventory
and specification is the review step; registering it is not a draft save. Existing
PRs cannot be adopted as new Work Items by this API. Resolve ownership of a partial
PR before creating replacement work; independent PR enrollment does not release
the original Item's dependents. See [Work plans](work-plans.md).

## Persistence, deployment and validation

Migrations `e14a217d0910` and `f25b328e1021` follow `d83ba105fc29`; apply the current
head with the matching server/UI version. The first adds question, answer and
resume receipt tables; the second adds Plan registration identity. A downgrade
removes these new records/keys, so take a backup before any rollback. Existing
Runs and Plans need no fabricated questions or request IDs.

Question/answer/receipt retention follows Run retention and cascades when the Run
is pruned. Work Item Run protections still apply. Plan registration keys remain
while their Plan remains; decision history is not a permanent independent archive.

REST resume now requires a JSON body with request ID and revision. Update saved
REST/MCP callers and deploy the matching UI. Refresh MCP discovery (22 work tools,
4 operations tools). Pause/cancel contracts retain their existing semantics.

Automated checks cover trusted/stale question collection, answer versus resume,
response-loss replay, concurrent PostgreSQL requests, stale revisions/PR heads,
delivery timeout recovery, migration round trips, MCP scopes and UI retry behavior.
Before marking this operational, deploy to an isolated canary target and record:
version, Plan/Run/PR links, provider question, saved answer, applied attempt,
delivery result, actual implementation/merge and replacement-work recovery.
No g-sandbox migration or Linear removal is required for this verification.

### devkit workflow requests

The engine's `current.requests` feeds the existing Decisions screen. A revision-
checked resume accepts `workflow_answer: {request, action, value?}` with actions
`accept`, `decline` and `cancel`. Integration approval still uses Hub's separate
approve/revise/revoke/reject controls. `decline` keeps a request open; `cancel`
records deferral and never revokes an approval or cancels the run.

Hub validates the current head/base and evidence digest, lets the pinned CLI
prepare the decision YAML in an isolated disposable checkout, then stores the
operator response and exact record with the resume receipt before dispatching.
The agent publishes it to the bound unit. The `autohub-decision:<UUID>` note is
its publication key: retries must not append it twice or overwrite another record.
Until the agent commits evidence, workflow evaluation does not advance on a saved
answer alone. The UI records acceptance before publication; agent failure remains
visible through the ordinary execution attempt and retry controls.

An accepted handoff may authorize a new workflow hash for the same spec anchor;
this is recorded in the run snapshot under `authorized_workflows`. It never
permits arbitrary rebinding or a different policy/runtime. A handoff requiring a
different anchor needs a separately enrolled unit. An explicit change request
uses `devkit workflow return` to void later approvals and reports; a stale-approval
notice alone does not void them. Repository decisions never grant Hub merge
permission or override its withheld approval, head/base checks or final merge fence.
