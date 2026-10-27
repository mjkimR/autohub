# Implementation and verification status

Implementation review: **2026-10-27**. Last recorded production baseline:
**2026-10-02**, Cloud Run revision `autohub-00015-4l4`, DB schema `autohub`.
This document has not rechecked the currently serving revision. Dated canaries
below establish their tested scope only; local changes do not establish deployment.

## Current local implementation

The [devkit integration guide](devkit-integration.md) is the entry point for SDD
runtime setup and the devkit/Hub responsibility boundary. Current capabilities:

| Area | Implemented behavior | Contract |
| --- | --- | --- |
| SDD activities | Planning/Development starts, fenced/recoverable proposal decisions, owning-base automatic approval, effort/review evidence, handoff, questions and integration approval | [Run decisions](run-decisions.md#native-sdd-decisions) |
| SDD runtime | devkit 0.1.4 monorepo pin, default/app-common profiles, repository mapping, missing-bundle checks and workflow/approval fencing | [devkit integration](devkit-integration.md) |
| Repository viewer | Shared devkit-viewer, selected-branch proposal roadmap, recorded Proposal → Spec → Run/PR lineage and Decisions links | [Viewer](repository-viewer.md) |
| Pipeline progression | Shared tick/webhook/manual driver; immediate ready transitions, bounded retries and preserved waits | [Advancement](development.md#pipeline-advancement) |
| SDK flows | Durable host, scoped approval and the existing-PR devkit bridge | [SDK contract](sdk-task-flow.md) |

### P2 second-review follow-up (2026-10-27)

The second review's three reproduced defects are fixed. Automatic Planning
acceptance now excludes Development handoff and requires the proposal's own
Planning branch. An automatic publication's internal error transition records a
specific recovery revision; generic resume reconciles the exact published commit
before dispatching more work. User changes do not extend that authorization, and
recovery also checks the original PR branch/base. Native gate inspection no longer
requires an implementation Attempt when approval was withdrawn while still queued.

New regressions exercise a real Git/devkit Development handoff, lost-result
recovery without another Attempt or publication, resume replay, and queued
withdrawal through explicit reapproval and merge. Recovery remains fenced after
revocation, cancellation, pending/dismissed questions, project disable and base
changes. The full backend suite with both reviewed SDD profiles and required
OS-isolated devkit execution passed **1,186 tests / 17 skipped**. PostgreSQL
passed 57 decision/merge cases with the reviewed runtime, including
publication/cancel contention. Lint, type checks, the production UI build, local
documentation links and whitespace checks passed. No API or database migration
is required; changes remain local.

### P1 review follow-up (2026-10-27)

The follow-up fixes three independently reproduced authorization defects: Hub's
own decision commit was treated as an unauthorized head change; proposal decisions
bypassed unapplied Hub questions; and automatic acceptance restored withdrawn
approval on a generic resume. Decision tests now move the PR to a distinct commit
and observe CI for that head. New regressions cover stale CI, other head changes,
open/answered questions, a question arriving during preparation or agent polling,
and explicit reapproval of withdrawn automatic delegation.

The full backend suite, with the reviewed SDD profiles and required OS-isolated
devkit execution, passed **1,177 tests / 17 skipped**. Targeted SQLite tests passed
126 cases (2 PostgreSQL-only skips), PostgreSQL passed 48 decision/merge cases,
and the frontend passed 207 tests. Lint, type checks, the production UI build,
documentation links and whitespace checks passed. The implementation and tests
are local; deployment and live GitHub/provider canaries remain outstanding.

### devkit alignment verification (2026-10-26)

The devkit 0.1.4 alignment was verified locally against immutable monorepo commit
`3609efe87e590c8da5f01a905cb207a13090f943`. Both reviewed runtime profiles were
provisioned in fresh directories; the previous installations were preserved.

| Verification | Result | Scope |
| --- | --- | --- |
| Full backend, SQLite with the reviewed SDD profiles | 1,163 passed / 17 skipped | Existing application behavior plus real Git, OS-isolated devkit, native decisions, handoff and SDK bridge |
| Required isolated SDD contract suite | 84 passed / 2 skipped | Backend subset; canonical/manual/policy acceptance, owning-base policy, 11-question rejection, runtime isolation and recovery |
| PostgreSQL decision/lineage/merge regressions | 39 passed | Publication/cancel locking, unknown push recovery, automatic decisions, revoked approval, project boundaries and merge fences |
| Frontend, normal parallel runner | 206 passed | Viewer, Planning evidence, saved-request recovery, roadmap and execution links |
| Standalone SDK | 27 passed; wheel and source distribution built | HTTP and remote contracts |

Lint, backend/SDK type checks, frontend type check and production build, generated
API consistency, receipt synchronization and whitespace validation passed. The
viewer tarball's SHA-512 matches the npm lock. The new runtime pin records all six
devkit distributions at 0.1.4.

The verification also corrected two test setup issues: SDD test packages now avoid
duplicate module names during full collection, and the Work Plan migration
roundtrip includes the existing `attach_branch` migration. AI Catalog form tests
wait for initial dialog autofocus before editing, removing their parallel-run race.
The review follow-up adds durable publication intents in existing resume receipts,
closes all questions on rejection (including more than the ten display rows),
supports delegated intent/acceptance, and preserves support-role rounds and effort
evidence before approval. It also prevents inspection from restoring withdrawn
proposal approval. No new DB migration is needed. A focused activity-start suite
passed 14 tests, including four hint/override/retry cases added after full collection.
There are three non-failing architecture warnings for existing direct HTTP client
construction sites. A Docker image build and live deployment/provider canaries
were not run for this update.

### Previous verification (2026-10-19)

Both change sets were verified locally on 2026-10-19. The suites overlap; counts
are not additive and do not represent a fresh full-application test run.

| Change set | Verification | Scope |
| --- | --- | --- |
| devkit consumer alignment | Unit 66 passed; isolated CLI/native/bridge SQLite 67 passed / 1 skipped; PostgreSQL 46 passed; UI 204 passed | Runtime profiles, workflow contract, approvals, handoff, bridge and viewer |
| Common advancement and follow-up fixes | Targeted SQLite 371 passed / 8 skipped; PostgreSQL 58 passed | Early CI repair after a draft wait, same-tick capacity release, quota/due-time and delivery deduplication |

Lint, type/build checks and whitespace validation passed for both changes.
Generated API consistency also passed for the devkit integration change.
The skipped SQLite lock-contention case is exercised by PostgreSQL coverage.

### Remaining rollout evidence

The latest changes have local verification, not a new production canary. Before
claiming deployment, build the container, apply the matching migrations, configure
runtime profiles, and verify isolation on the serving host. Then run the
[live SDD canary](devkit-integration.md#live-canary-after-deployment) and record the
revision, Run/PR links and approval history. Actual provider replies, GitHub CI and
merge behavior cannot be inferred from local fixtures.

## Recorded production baseline (2026-10-02)

| Area | Verified | Details |
| --- | --- | --- |
| PR automation | Registration, Codex implementation, CI failure fixes, conflict resolution, current-head CI check, automatic merge, concurrency limit | [Canary 09-22](canary-results-2026-09-22.md) |
| Approval and recovery | Draft approval/withdrawal, polling recovery for missed webhooks | [Execution architecture](architecture.md) |
| AI Catalog and Jules | Default catalog installation and additional creation, explicit selection, quota/concurrency limits, automatic task PR registration and merge, report storage | [Catalog guide](ai-catalogs.md) |
| Project connection | Automatic dispatcher creation and recovery, blocking edits to owned schedules, Codex/Jules connection tests and cleanup | [Connection tests](project-detail-and-connection-tests.md), [Canary 10-01](canary-results-2026-10-01.md) |
| Shared maintenance and retention | One `System maintenance` per installation, history retention policy, first successful production cleanup | [Operating procedure](development.md#system-maintenance) |
| Authentication and deployment | Account login and token refresh, managed machine keys and scope isolation, workbench deployment path | [Deployment guide](cloud-run-deployment.md) |
| Google login and signup approval | Real-account signup→approval→suspension/reactivation→permission check, `query` and `form_post` callbacks | [Google authentication](google-auth.md) |
| MCP | 25 tools at work `/mcp/` (13 read, 12 write, `autohub:mcp:read/write`), 4 at operations `/ops/mcp/` (`autohub:mcp:ops`). Argument errors return per-problem `details` | [Connection guide](mcp.md), [Canary 10-01](canary-results-2026-10-01.md) |
| WorkPlan and WorkItem | Plans tab, Plan/Item dependencies, pause/resume/revoke, follow-up runs right after registration and merge, Issue sync right after webhooks | [Canary 09-23](canary-results-2026-09-23.md), [Canary 09-28](canary-results-2026-09-28.md) |
| Plan MCP registration | Idempotent registration by project + request key with a content digest, `group_key` classification and Plan/Run group filters | [Canary 10-01](canary-results-2026-10-01.md) |
| Questions, answers, and resume | Codex PR question marker detection→`blocked`, separate answer storage and resume, answers pinned to a new attempt, request-key idempotency | [Canary 10-01](canary-results-2026-10-01.md) |
| Codex reply handling | Connection test slot release, 5-minute detection of replies without pushes, `[bot]` author recognition | [Canary 10-01](canary-results-2026-10-01.md) |
| Stop and recovery | Holding external pushes while a Run is paused, return to CI observation on resume after a push, Plan pause/resume, Run cancel, Plan revoke, replacement Plan with a link to the original | [Canary 10-02](canary-results-2026-10-02.md) |

Contracts are in [Run decisions](run-decisions.md), [Work plans](work-plans.md), and
[MCP](mcp.md). Defects found in the 2026-10-01–02 canaries were corrected in `dc8fc8b`,
`74f8f53`, `fa9bea7`, `746959d`, and app-common `a36b829` (showing the cause of MCP
argument errors).

## Recorded deployed scope without a live canary (2026-10-02)

Confirmed only by automated tests.

- [Work Plan backlog and activity](work-plan-backlog.md): `draft` and `proposed` states
  (no PR, Run, or Issue created), `paused` option at registration, adding and removing
  Items in Draft and Proposed, comments and before/after edit history, MCP
  `work_plans_activity` and `work_plans_comment`. Comment editing, deletion, threads,
  notifications, and GitHub comment sync are not supported.
- [Classification change](work-plans.md#group-classification): REST
  `PATCH /{plan_id}/group`, MCP `work_plans_set_group`. It checks the revision and records
  history, and does not change execution, state, or specs.

## Earlier implementation and validation evidence

These entries preserve the evidence collected at the time. Current contracts above
supersede historical specrig and viewer descriptions; these entries are not a rollout checklist.

- 2026-10-14 SDD transition: project types, APIs, and screens were consolidated as `sdd`,
  and the `devkit-spec` provider and Python runtime lock are pinned for execution. devkit
  requests/answer/return, explicit handoff within the same spec, and the existing approval
  and merge protections are connected. Old execution evidence is preserved, and
  in-progress runs are terminated by the migration. Real CLI and macOS isolation,
  response, screen, and DB regression tests were added. Real container, PostgreSQL, and
  GitHub connections are not part of the completion evidence for this item. At that point, Linux
  namespace support and additional bundle profiles remained deployment work. The
  2026-10-19 implementation adds profiles and PostgreSQL evidence; live host
  verification remains separate. Current setup follows the
  [devkit integration guide](devkit-integration.md). Final local verification:
  backend SQLite 972 passed / 31 skipped, separate real CLI integration 44 passed /
  1 skipped, UI 187 passed, SDK 27 passed. Lint, type checks, UI/SDK builds, and the
  generated API consistency check also passed. The test suites partly overlap, so the counts are not summed.

- 2026-10-12 specrig integration hardening (historical; the current implementation is
  replaced by the SDD transition above): if a stop, cancel, or approval withdrawal occurs
  during the last GitHub lookup, the revision/lease is rechecked before the merge request.
  The pinned release CLI, Git, and offline restore cache are included in the image, and
  layered fresh checkout restore and real CLI tests of release/follow-up sources are
  connected. The historical release pin was 0.1.2, and layered sources are test-only. Per-spec run
  links and review/final report summaries were added. Custom Go rules are outside the
  shared server's support scope, and installation and execution errors are distinguished
  from rework for rule violations.
  [Operating procedure](development.md#native-sdd-runtime). Docker image build,
  PostgreSQL, and real GitHub canaries were not part of this local verification.

- 2026-10-12 native specrig HITL improvements: applied questions, answers, and rework
  requests are passed to later steps, and unchanged answers are distinguished from rework
  waits. At G3, evidence is recorded by PR ready observation or Hub approval, and draft
  waits are polled without an execution slot. Explicit reapproval is required after
  withdrawal or feedback. Decision history and draft merge conditions are shown in the UI.
  [Contract](run-decisions.md#native-sdd-decisions). The Decisions screen was restructured
  around the current question, approval evidence, and next action, and decision history
  was moved to a secondary area. Change request and stop reasons are entered on selection
  and shown in one column on mobile. Production deployment and real GitHub canaries were
  not performed.

- [autohub-sdk](../packages/sdk/README.md): `@pipeline` declarations, input/output
  validation, `Registry`, JSON manifest export, local execution examples. 0.2.0 provides
  task/approval sequential FlowSpec, release/run/command wire models, and an HTTP client.
  Real HTTP registration, execution, waiting, resume, and error scenarios are verified
  against the mock in planhub's independent environment. The current scope is in the
  [SDK contract](sdk-task-flow.md). The real backend's catalog, run, and command APIs, DB
  ledger, lease, revision fencing, and native/HTTP worker adapters are also implemented
  locally. Real SDK HTTP calls, DB restarts, and PostgreSQL contention were verified. The
  devkit-spec PR bridge is also locally implemented and tested; see
  [its current contract](sdk-task-flow.md#planhub-pr-bridge). Worker provisioning and
  production rollout remain deployment work.

## Operating constants and compatibility

- The schedule tick is 5 minutes (`*/5 * * * *`). The 60 seconds for projects/maintenance
  is an internal minimum interval. Current PipelineRun advancement can continue
  immediately through ready steps; see [pipeline advancement](development.md#pipeline-advancement)
  and [Work Plan admission](work-plans.md#registration-and-dependencies) for trigger
  budgets and waits. The external tick remains the recovery path.
- Authentication uses `X-API-Key`. `APP_API_KEY_ROOT_KEY` is for machine management only and is not an MCP credential.
- REST resume requires `request_id` and `expected_revision`. The Plan registration key is required in MCP and optional in REST.
- Shared maintenance entries cannot be edited, stopped, or deleted through the API/UI and are recovered at startup and on each tick.
- Branches of failed or canceled connection tests are deleted 24 hours after they end.

| History | Retention |
| --- | --- |
| Successful schedule job | 3 days after completion |
| Failed schedule job | 7 days after completion |
| Finished pipeline run | 30 days after last change, including child attempts/deliveries/replies, questions, and answers |
| Webhook delivery | 90 days |

Up to 1,000 jobs and 200 runs are cleaned up once per hour. Waiting or retryable jobs,
active/paused/blocked runs, valid leases, and runs referenced by unresolved WorkItems are
preserved. Run expiry does not lead to PR re-registration.

Migrations: `f4d5e6f7a8b9` (shared schedule), `a5e6f7a8b9c0` (run expiry marker),
`b6f7a8b9c0d1` (authentication), `c7d8e9f0a1b2` (work plan), `e14a217d0910` and
`f25b328e1021` (questions, answers, registration key), `b47d540a3243` (backlog and
activity), `c58e651b4354` (group key). The `b47d540a3243` downgrade is refused while Draft
or Proposed plans remain, and it drops the activity tables. The `c58e651b4354` downgrade
removes only the classification values.

## Excluded and deferred

- Not triggered live: Telegram, Jules quota exhaustion/429, required review and branch
  protection, connection test timeouts, lost responses, and authentication failures,
  actual deletion of expired rows, Plan edit revision conflicts, Plans mixed with CI
  failures, and the unverified features above. All are covered by automated tests.
- Out of scope: bulk control, policy, quota, and path locks per classification, cross-Plan
  Item dependencies, a failed Item retry API and automatic successor substitution, Jules
  question collection, automatic planning/WBS, dynamic catalog selection, pre-merge LLM
  review. Branching policy for additional repositories is decided at onboarding. Provider
  uncertainty is in
  [Catalog open items](ai-catalog-implementation-notes.md#known-limitations-and-remaining-work).
- Multiple devkit proposals, milestone batch execution and Work Plan linkage are
  deferred; see the [scope and unresolved decisions](devkit-integration.md#deferred-multiple-proposals-and-milestone-execution).
- Known cleanup item: Plan registration requests issue many queries (query counter warning). Behavior is not affected.
