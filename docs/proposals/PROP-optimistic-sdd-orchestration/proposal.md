---
id: PROP-optimistic-sdd-orchestration
title: Delegate SDD execution to repositories and agents
summary: "Remove Hub-side SDD runtime preparation and workflow evaluation. Start repository work optimistically through ordinary PR delivery and observe repository-owned GitHub Actions checks."
status: accepted
created_at: 2026-11-13
target_area: capabilities/sdd/
priority: high
size: L
planning_effort: high
dev_effort: high
boundaries:
  owns:
    - modules/hub/app/features/project_management/
    - modules/hub/app/features/execution/flows/
    - modules/hub/app/features/execution/tasks/domains/maintenance/
    - modules/hub/app/mcp/
    - modules/hub/migrations/
    - modules/hub/tests/
    - modules/hub-ui/src/
    - packages/sdk/
    - config/
    - scripts/
    - docker/
    - .github/workflows/
    - justfile
    - docs/
    - README.md
  excludes:
    - .devkit/managed/
    - .agents/skills/
    - .codex/
    - .devkit/config.toml
    - pyproject.toml
    - uv.lock
task_kind: feature
workflow: sdd-proposal
---

# [PROP-optimistic-sdd-orchestration] Delegate SDD execution to repositories and agents

## 1. Background & Hypothesis

Hub prepares a repository-specific devkit runtime, restores its managed assets,
evaluates its workflow and dispatches one stage at a time. This makes repository
setup and correctness prerequisites of Hub orchestration. The intended boundary
assigns those responsibilities to the repository and its working agent.

Hub should start requested work optimistically and retain its existing PR owner,
operator questions, delivery identity, retries and GitHub CI/merge observation.
Hub-side `devkit sync` is removed without a replacement runner or Actions job.
Repository verification, when configured, executes in repository-owned GitHub
Actions. This does not change Auto Hub's own contributor SDD workflow.

## 2. Planning Decisions

Baseline: `main` at `9cc90ff27daa15256ea38488464e6330089d8a69`. This request
has no prerequisite unit. The local checkout was clean, so Planning uses
`plan-optimistic-sdd-orchestration` in this checkout under `worktree=auto`.
Remote branch absence could not be checked because origin DNS was unavailable;
no push or remote operation succeeded.

The Scout inspected the existing PR lifecycle and identified the coupling in
`MAT-optimistic-sdd-boundary`. This is source inspection,
not an executed runtime or deployment claim.

| Option | Responsibility | Cost and consequence |
| --- | --- | --- |
| Keep the embedded evaluator | Hub installs devkit, restores assets and decides each stage. | Preserves native guarantees but retains the responsibility being removed. |
| Move the evaluator to Actions | Hub requests remote evaluation and consumes its result. | Adds a remote protocol and still makes Hub enforce repository workflow. No requirement justifies it. |
| Optimistic PR orchestration (selected) | An agent owns repository setup, SDD interpretation and progress; Hub owns delivery, questions and GitHub observations. | Removes preflight guarantees. Invalid work can consume an attempt before the agent reports a problem. |

### Responsibility boundary

- Start intent is explicit: project, base branch, proposal/spec path, Planning or
  Development and optional catalog/effort. This is a work request, not proof that
  the repository is eligible for the requested phase.
- Hub validates authorization, enabled project/connector/catalog, input shape,
  live GitHub refs and exclusive ownership. It does not validate SDD adoption,
  proposal status, size, prerequisites, receipt freshness, lock or bundle content.
- Hub creates an activity branch and a Draft PR using GitHub APIs. It does not
  check out the repository or make a proposal-status edit. Existing exact
  request/branch/PR ownership guards remain necessary for response-loss recovery.
- The agent follows the repository's instructions until its work is finished or
  needs operator input. Hub does not name the next devkit stage, tell it to run
  `sync`, prescribe repository setup, or author acceptance/handoff/answer records.
- Reuse the existing implementation request, PR push observation and
  `RunQuestion`/`RunAnswer`/explicit resume. No replacement worker-result API,
  SDD report signature, workflow JSON interpreter or remote evaluator is added.
- Both Planning and Development launches stay Draft until the operator marks the
  PR ready. The agent is instructed to leave ready/merge to the operator and Hub.
  Once ready, existing project auto-merge policy and current-head GitHub CI apply.
  Repository-internal gates remain the repository/agent's responsibility; Hub
  does not claim to enforce them. Pushes or generic answers do not mark PRs ready.
- Preserve question ingestion around pushes: an observed current-attempt question
  pauses the Run before CI/merge progression, including a question posted after a
  push while the PR is Draft. Reuse correlation/head fences; do not reintroduce
  repository workflow evaluation to decide whether the question is valid.

### Removal inventory

| Area | Remove | Retain or simplify |
| --- | --- | --- |
| Runtime | `lock_runtime.py`, `runtime_cache.py`, `runtime_install.py`, `runtime.py`, SDD OS isolation, runtime probes and install diagnostics | No replacement evaluator environment, local checkout or source-token access for evaluation |
| Evaluator | `services.py` workflow evaluation; `policy.py` adoption/size/stage checks; runtime/workflow/configuration evidence hashing; envelope interpretation | Optional unit path and activity intent as descriptive execution metadata |
| Stage control | `progress.py` stage selection/redispatch; server acceptance/rejection/handoff/return/answer publication; `decisions.py`, `plan_decisions.py`, `plan_publication.py`, `answer_publication.py`, `gates.py` and evaluator-only report projections | Ordinary PR controls, correlated agent questions and explicitly selected answers; legacy decision history remains read-only |
| Discovery | Native workflow decision generation and readiness-derived actions | Generic Run questions and existing non-SDD decision owners; retained native evidence is historical |
| Milestones and batches | Executable milestone preview, graph/eligibility analysis, batch creation/resume/admission and SDD batch maintenance | Repository document browsing and historical batch/claim reads; Stop can settle an old local owner without starting new work |
| SDK bridge | Both evaluator-coupled `autohub.sdd:*` and `autohub.pr_delivery:*` built-in bindings, checkout/evidence configuration and bridge dispatch | Generic SDK tasks/flows/approvals and ordinary scoped PR resume APIs; no replacement built-in bridge |
| Public surfaces | Runtime/readiness/milestone-evaluation endpoints; native typed workflow mutation APIs; batch execution mutations and matching MCP tools | Single-activity starts, run links, ordinary questions/controls and historical reads |
| Packaging and tests | `config/sdd-runtime`, `config/sdd-build`, installer and SDD test scripts/recipes, SDD image stages/env/cache/bubblewrap, evaluator-only CI job and source credential requirement | Auto Hub contributor devkit dependencies, `just init hub`, normal backend/UI/SDK checks and normal GitHub CI observation |

`CAP-SDD-native-delivery` becomes optimistic activity dispatch.
`CAP-SDD-workflow-control` and `CAP-SDD-runtime-isolation` cease to promise live
workflow/runtime evaluation. `CAP-SDK-existing-pr-bridge` is retired with its
built-in bindings. Historical records and IDs remain readable; no evaluator
fallback is kept for them. Delete evaluator-only tests and replace them with
regressions for the new boundary and retained orchestration.

### Scope Excluded

- Creating a GitHub Action, remote devkit runner or check-result ingestion protocol.
- Delegating `devkit sync` to a runner or Action as a substitute for its removal.
- Reimplementing devkit rules, workflow gates or dependency resolution in Hub.
- Replacing native milestone batches with a new operator-authored queue system.
- Changing generic SDK runtime isolation, ordinary CI verification semantics,
  provider adapters, Work Plans or Auto Hub's own SDD contributor process.
- Deleting historical runs, attempts, batch selections, decisions or PR links.

### Historical and in-flight work

The cutover stops new legacy-native admission before changing its dispatch path.
A data migration marks every nonterminal old native Run canceled with an explicit
retirement reason, invalidates its lease and settles local active attempts.
It stops legacy batches, fences their claims and retains exact saved remote
artifacts and uncertainty. It does not issue GitHub writes or pretend to cancel
provider work. Terminal history is unchanged. A new optimistic Run uses an
explicit execution-version discriminator, not truthiness of `sdd_snapshot`.

Old native resume/approval and old batch create/resume are refused with HTTP 410
`SDD_EXECUTION_RETIRED`. Synchronous legacy bridge registration/start/control
boundaries refuse new effects with HTTP 410 `SDD_BRIDGE_RETIRED`. Undispatched
legacy bridge steps are durably retired before claiming. Outstanding attempts
without a saved resume receipt settle with a terminal failed `WorkerResult`
carrying `SDD_BRIDGE_RETIRED`, rather than entering transient-unavailable retry.
Receipt-backed deliveries retain observe-only progression of their existing PR
owner and never repeat resume. Refusal performs no checkout, CLI or remote
mutation. An undelivered legacy bridge claim cannot create a new effect.
Migration preserves completed flow results.

History reads retain old snapshots and immutable attempt requests. No generic
resume implicitly converts an old Run. Starting another Run for the same PR
requires an explicit reconciliation acknowledgment after inspecting any
previously dispatched work; uncertain old activity claims keep their ownership
reservation until that acknowledgment records the exact candidate. Operator
rollout guidance covers external agents still working after local cancellation.
A downgrade never reactivates a retired Run, batch or claim.

### Related open proposal disposition

The user authorized rejection of related open proposals. Inventory covers the
six other proposal anchors returned by `docs list proposal --all-namespaces
-n 0`; target blueprints are not additional work requests.

- `PROP-run-origin-links` stays accepted: Work Item/Work Plan/provider-session
  origins remain useful. Its native SDD unit/batch links target read-only retained
  subjects after this cutover; readiness and batch-control behavior is removed
  from its future contract. Historical origin links need no runtime.
- `PROP-updated-at-maintenance` stays accepted: timestamp correctness is
  independent of repository validation. Its SDD batch examples apply only to
  retained owner writes that still exist; deleted execution paths add no work.
- `PROP-schedule-config-ownership`, `PROP-jules-antigravity-migration`,
  `PROP-owed-counts-error-reason` and `PROP-sidebar-overflow-cues` are independent.

No open proposal has embedded SDD evaluation as its sole outcome, so none is
rejected wholesale. The removed design is implemented history in completed specs
and accepted ADRs. The preliminary decision identifies the ADRs to supersede.
Development rechecks the inventory and aligns surviving partial proposals under
exclusive ownership before they are used for a later handoff. If another live
branch owns one, coordinate that change rather than rewriting it from this task.

### Acceptance and verification

- **OPT-01**: Given a repository with no devkit lock, missing receipt or unsupported
  Python requirement, when an authorized activity starts, then Hub dispatches the
  requested work without installing dependencies or evaluating repository setup.
- **OPT-02**: Given a requested proposal whose status/size/prerequisites do not
  satisfy devkit, when work starts, then Hub does not reject it on those grounds;
  the agent may report the repository problem through its normal question path.
- **OPT-03**: Given Planning or Development start and a repeated request after a
  lost response, then the same owned branch/Draft PR/Run is recovered. No server
  proposal-status commit, checkout, `sync` or workflow evaluation occurs.
- **OPT-04**: Given an implementation request, then it names intent/unit/effort and
  repository instructions without an evaluated stage or single-stage stop. Agent
  questions, selected answers and explicit resume use existing durable identity.
- **OPT-05**: Given a correlated question before or after an agent push, then the
  Run waits for input; a saved answer alone neither resumes nor grants merge.
  A late question cannot be bypassed just because the head advanced.
- **OPT-06**: Given an agent push and no open question, then existing configured
  GitHub CI observation proceeds. Draft never merges; ready plus current-head CI
  and project policy can merge. Head changes and return to Draft invalidate any
  in-flight merge decision without repository workflow reevaluation.
- **OPT-07**: Given the application/worker/MCP routes, then no retained request can
  reach a devkit command, runtime install, source build, local repository checkout
  or native workflow interpreter. Removed UI controls cause no background probes.
- **OPT-08**: Given a legacy native Run/batch/claim, then migration preserves its
  history, ends local progression, fences stale workers and refuses conversion
  or resume. Explicit reconciliation is required before uncertain ownership can
  be released to new work. No external cancellation or successful merge is invented.
- **OPT-09**: Given a built-in bridge binding or old bridge flow, then no runtime
  check or fresh PR-resume effect runs. A receipt-backed already resumed delivery
  can observe its owner; generic SDK flows and standalone SDK dependencies work.
- **OPT-10**: Given an SDD document view or historical Run/batch link, then the
  operator can browse the exact available subject and see its retired status
  without readiness claims, actionable native decisions or execution controls.
- **OPT-11**: Given the serving image and ordinary project setup, then no SDD build
  environment, cache, sandbox probe or source-read credential is required. The
  contributor's own devkit setup and checks continue to run.
- **OPT-12**: Given reconciled documents and live proposal scopes, then active
  contracts describe repository-owned setup/execution, accepted runtime decisions
  have the correct supersession, and no retained proposal requires live SDD
  eligibility/control on a retired historical surface.

Development runs focused backend API/progression/question/migration tests,
PostgreSQL ownership races, UI integration tests for removed controls/history,
SDK bridge retirement and generic flow regressions, plus `just lint`, `just
check`, `just docs-check`, `just gen-ui-api`/`just check-ui-api`. If standalone SDK
code changes, run `just test-sdk` and `just build-sdk`. These are required future
checks; Planning reports its own executed checks separately. No deployment,
provider or live GitHub result is inferred from local verification.

## 3. Proposed Delivery

One feature spec delivers the responsibility change across dependent consumers.
Implement the new execution discriminator and legacy fences before routing new
activity work through ordinary PR delivery. Remove native evaluation/control and
bridge entrypoints, then evaluator modules/assets. Simplify UI/MCP/generated API,
reconcile owning contracts and supersede decisions in the same delivery.

The PADR is `PADR-repository-owned-sdd-execution`. Its promoted ADR is the
responsibility decision; the detailed acceptance examples above become the spec.
No separate replacement runner or scheduling project is required for completion.

## 4. Lifecycle & Retirement Criteria

The proposal is reviewing until the concrete removal scope passes `plan-accept`.
On acceptance, promote its PADR during handoff and implement the single feature
spec. Do not describe capabilities as changed until the implementation lands.
Retain completed specs as history. Rejection records the decision without deleting
history or changing currently implemented behavior.
