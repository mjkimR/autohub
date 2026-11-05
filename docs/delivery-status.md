# Implementation and verification status

Implementation review: **2026-11-05**. Last recorded production baseline:
**2026-10-02**, Cloud Run revision `autohub-00015-4l4`, DB schema `autohub`.
This document has not rechecked the currently serving revision. Dated canaries
below establish their tested scope only; local changes do not establish deployment.

## Current local implementation

The [devkit integration guide](devkit-integration.md) is the entry point for SDD
runtime setup and the devkit/Hub responsibility boundary. Current capabilities:

| Area | Implemented behavior | Contract |
| --- | --- | --- |
| SDD activities | Planning/Development starts, fenced/recoverable proposal decisions, owning-base automatic approval, effort/review evidence, handoff, questions and integration approval | [Run decisions](run-decisions.md#native-sdd-decisions) |
| SDD runtime | devkit monorepo pin, default/app-common profiles, repository mapping, missing-bundle checks and workflow/approval fencing | [devkit integration](devkit-integration.md) |
| Repository viewer | Shared devkit-viewer, selected-branch proposal roadmap, recorded Proposal → Spec → Run/PR lineage and Decisions links | [Viewer](repository-viewer.md) |
| Pipeline progression | Shared tick/webhook/manual driver; immediate ready transitions, bounded retries and preserved waits | [Advancement](development.md#pipeline-advancement) |
| SDK flows | Durable host, scoped approval and the existing-PR devkit bridge | [SDK contract](sdk-task-flow.md) |

### devkit v0.1.6 호환성 후속 작업 (2026-11-05)

버전 갱신 뒤 확인한 네 가지 보완을 순서대로 반영했다.

1. `just test-sdd-pg`를 추가해 필수 런타임 검사를 유지한 채 PostgreSQL SDD 계약을
   실행한다. 기존 `sdd-contract` CI 작업은 두 런타임을 설치한 뒤 SQLite와 PostgreSQL을
   모두 검증한다. 게시·취소 행 잠금 경합도 이 경로에 포함된다.
2. `just check-devkit`이 세 Python 환경의 source·override·lock에 기록된 커밋·버전,
   뷰어 source receipt의 출처·SHA-256, npm 무결성을 오프라인으로 비교한다. Backend
   lint와 SDD CI의 런타임 설치 전에 실행하며, 불일치는 `DEVKIT_PINS_INVALID`로 실패한다.
3. 운영자 질문 답변에 `by: user`를 기록하고 devkit 게시 요청에도 전달한다. 이전에 저장한
   운영자 답변은 재게시할 때 이 값을 보완한다. 제안 거절로 질문을 닫는 답변에도 결정
   권한을 기록하며, 실제 사용자 식별자는 기존 Run·operation·commit 기록에 남는다.
4. 실제 devkit worker의 `scope_extensions`를 Hub 보고서에 보존하고 Planning·Development
   승인 화면에서 추가 파일·태스크·이유·요구사항을 표시한다. 해당 보고서는 기본으로 펼친다.
   이전 보고서는 그대로 읽을 수 있으며 기존 승인·head/워크플로 검증을 유지한다.

최종 전체 백엔드 회귀는 **1,237개 통과 / 17개 건너뜀**이다.
핀 불일치·이전 답변 호환을 포함한 집중 백엔드 검사 62개, 실제 CLI 메타데이터 검사
5개, PostgreSQL SDD·브리지 계약 110개, 최종 UI 검사 215개가 통과했다.
`just lint`, `just check`, `just check-ui-api`, 새 검사 스크립트의 Ruff·Pyright,
셸/YAML 구성 검사와 문서 링크 검증도 통과했다. 저장소 전체 rules 검사는 오류 0건,
기존 경고 3건이다. GitHub Actions 원격 실행과 운영 배포는 수행하지 않았다.

### devkit v0.1.6 검증 (2026-11-05)

개발 환경과 기본/app-common SDD 프로필의 manifest·lock을 devkit 0.1.6 커밋
`b151a10bb4ab9433c1dbaeb6c316917c959b6ba0`으로 맞추고, 새 환경에서 자산을
동기화했다. 두 SDD 프로필은 기존 환경을 덮어쓰지 않고 `.cache/sdd-v016`과
`.cache/sdd-app-common-v016`에 설치해 검증했다.

`incubation` → `adaptive-dev` 변경에 맞춰 Planning/Development 시작, 제안 승인,
Proposals 화면의 동작 제한과 오류 안내를 수정했다. 기존 실행 기록의 `incubation`도
같은 제한으로 해석한다. 실제 CLI에서 이전 설정이 거절될 때 새 설정명을 안내하는
회귀 테스트를 추가했다. Hub의 승인·게시·handoff 경로는 기존 CLI 계약을 유지하며,
devkit의 composed acceptance/integration 명령은 호출하지 않는다.

같은 커밋에서 devkit-viewer 아티팩트를 다시 빌드하고 npm 무결성 값을 갱신했다.
전역/패키지별 roadmap과 각 `_archive`에서 선택한 브랜치의 제안을 열고 실행 단위로
연결하는 동작을 네 가지 경로로 검증했다.

| 검증 | 결과 | 범위 |
| --- | --- | --- |
| 전체 백엔드, SQLite + 새 SDD 프로필 | 1,218 통과 / 17 건너뜀 | 전체 회귀 및 실제 Git·격리 CLI |
| 필수 격리 SDD 계약, SQLite | 106 통과 / 2 건너뜀 | 승인, 거절, 복구, handoff, 프로필 선택, SDK 브리지; 행 잠금 경합 2건은 PostgreSQL에서 검증 |
| SDD 계약·SDK 브리지, PostgreSQL | 108 통과 | 행 잠금·게시 취소 경합 포함, 건너뜀 없음 |
| 프런트엔드 | 210 통과 | 새 viewer와 전역/패키지별·보관 roadmap |
| 독립 SDK | 27 통과 | HTTP 및 원격 계약; wheel·sdist 빌드 성공 |

`just lint`, `just check`, `just check-ui-api`, 세 환경의 `uv lock --check`,
`devkit status`, `devkit sync --check`, 문서 파일 링크와 `git diff --check`가 통과했다.
저장소 전체 `devkit rules check`는 오류 0건이며 기존 HTTP 클라이언트 경고 3건이
남아 있다. 운영 배포, Docker 이미지 빌드, 실제 GitHub canary는 실행하지 않았다.
기존 서버의 런타임 경로 전환과 활성 실행 정리는 [전환 절차](devkit-integration.md#assign-repositories)를 따른다.

### devkit v0.1.5 verification (2026-10-29)

The devkit v0.1.5 upgrade was verified locally against immutable monorepo commit
`96f34f89b689bf73a5cf225224d93583249c3bf3`; the reviewed manifests and locks under
`config/sdd-runtime*` recorded it for that verification. The follow-up aligned Hub with v0.1.5 behavior: an
XL draft is refused at Hub's Planning start with devkit-spec's size gate as the
reason, an `incubation` development approach refuses starts and acceptance before
any write, the new configuration refusals carry fix hints, `ux-review` rounds appear
in Planning evidence, and the runtime pin records `devkit-docs`.

| Verification | Result | Scope |
| --- | --- | --- |
| Full backend, SQLite with the reviewed SDD profiles | 1,215 passed / 17 skipped | Existing application behavior plus size gate, incubation refusals and real Git/OS-isolated devkit |
| Required isolated SDD contract suite | 105 passed / 2 skipped | Adds real-CLI XL size-gate and `SPEC_LIFECYCLE_INACTIVE` cases |
| Frontend | 207 passed | Planning evidence now includes a UX review round |
| Standalone SDK | 27 passed | HTTP and remote contracts |

Lint, backend/SDK type checks, frontend type check and production build, generated
API consistency and whitespace validation passed. A repository-wide
`devkit rules check` reports no errors (three existing HTTP client warnings); the
`spec` CLI citations are unchecked because devkit-spec runs only in the isolated
runtime. PostgreSQL, a Docker image build and live canaries were not run.

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
