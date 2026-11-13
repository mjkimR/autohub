---
id: ARCH-11-risks-and-technical-debt
title: Risks and technical debt
summary: "Records source-defined recovery limits, external cooperation requirements, verification gaps and retained scope constraints that affect Auto Hub's execution and access guarantees."
status: active
---

# [ARCH-11-risks-and-technical-debt] Risks and technical debt

These boundaries describe the implemented system. They are not ranked roadmap
items or evidence that a production incident occurred. Owning capabilities define
the contracts; this document identifies consequences and conditions that require
their treatment to be reconsidered.

## Uncertain external effects

- **Kind**: distributed-system constraint.
- **Boundary**: an external provider, GitHub push or worker operation can succeed
  before Hub receives or persists its response. Database leases do not make that
  remote effect exactly once. A sent request can outlive pause or cancellation.
- **Consequence**: a blind retry can duplicate work, while treating uncertainty as
  failure can discard a completed effect or leave cleanup ownership unresolved.
- **Treatment**: retain intent and identity, reconcile the owning attempt and keep
  unknown outcomes visible under `CAP-PR-pull-request-delivery`,
  `CAP-SDD-native-delivery`, `CAP-CONN-connection-verification` and
  `CAP-SDK-task-flow-execution`. Reconsider recovery whenever an adapter changes
  its identity, lookup, publication or cancellation semantics.

## Cooperating SDK worker receipts

- **Kind**: external cooperation requirement.
- **Boundary**: the HTTP worker's durable receipts, same-attempt replay and
  authoritative absence responses are obligations of that worker. Hub cannot
  infer those properties from a successful registration or HTTP connection.
- **Consequence**: a worker that loses receipts or falsely declares absence can
  execute an already completed attempt again despite Hub retaining its own intent.
- **Treatment**: treat `CAP-SDK-task-flow-execution` as a bilateral protocol;
  validate the selected worker's receipt/recovery behavior before relying on it.
  Revisit when deploying a different worker implementation, changing its receipt
  retention, or replacing its persistence. A host fixture cannot establish another
  worker deployment's cooperation.

## Immediately terminal provider-session creation

- **Kind**: source-visible collection gap.
- **Boundary**: `JulesSessionService.start` applies the create response with
  `_apply`; final-message collection occurs in `_observe` for unfinished sessions.
  A create response already marked `completed` does not pass through that
  final-message path. Completed task adoption is a separate collection pass.
- **Consequence**: an immediately completed session can retain its terminal state
  without the report text the operator expects. The inspected completion tests
  cover collection of a previously tracked session, not this create-response edge.
- **Treatment**: retain an absent summary as missing evidence rather than a
  delivered report. `CAP-AGENT-provider-sessions` bounds the collection guarantee.
  Revisit when provider creation can return terminal results or the start/collection
  boundary changes; no API for reconstructing that report is asserted here.

## Provider quota and session uncertainty

- **Kind**: external API knowledge limit.
- **Boundary**: Jules HTTP `429` does not identify daily quota versus concurrency
  exhaustion in the implemented interpretation. The effect of `sendMessage` or
  repeated PR comments on daily usage, and queueing at the provider's concurrency
  limit, is not established by Hub's source or fixtures.
- **Consequence**: the conservative hold can delay work longer than a provider
  concurrency pause, while provider activity outside Hub remains absent from its
  admission ledger. Session lookup and message collection also have bounded scans.
- **Treatment**: preserve the conservative behavior and explicit missing evidence
  in `CAP-AGENT-catalog-admission` and `CAP-AGENT-provider-sessions`. Revisit after
  provider contract changes or representative live responses establish a different
  interpretation. Do not substitute configured policy values for discovered
  provider entitlements.

## Database concurrency evidence

- **Kind**: verification boundary.
- **Boundary**: SQLite exercises default logic but does not establish PostgreSQL
  row-lock, publication/cancel or worker-lease contention behavior. Relevant
  integration tests explicitly skip those cases without PostgreSQL.
- **Consequence**: a passing SQLite suite can leave the serving database's
  competing-command and cancellation guarantees unverified.
- **Treatment**: retain separate PostgreSQL evidence for concurrency claims in
  `CAP-SDD-native-delivery` and `CAP-SDK-task-flow-execution`. Revisit affected
  contention coverage when transaction ownership, locking, lease checks or
  publication boundaries change. Test selection and outcomes must identify the
  database actually exercised.

## Runtime drift and admitted work

- **Kind**: compatibility and trust constraint.
- **Boundary**: the evaluation runtime follows each evaluated commit's own
  `uv.lock` (`ADR-repository-locked-runtime`). A changed runtime identity on a
  later head continues an admitted run; its effective workflow, policy and
  configuration identity still refuse unauthorized change. A pull request can
  change its lock, or an in-repository bundle it locks as a path source
  (`ADR-repository-path-sources`), and so the devkit rules that judge it; the
  user accepted that risk in the ADR.
- **Consequence**: a devkit bump inside a run changes the evaluator without
  re-enrollment; a bump that changes the effective workflow still leaves the run
  unable to continue. Runs, batch selections and bridge claims admitted under
  server-profile identities compare against a different `cli_version` format and
  batch `runtime` shape.
- **Treatment**: use the snapshot and refusal boundaries in
  `CAP-SDD-runtime-isolation`, `CAP-SDD-native-delivery` and
  `CAP-SDK-existing-pr-bridge`. Settle active native runs, open batch selections
  and approved bridge claims before rolling this runtime model out and again
  before rolling it back ([operations](../operations/sdd-runtime.md#rollout-and-rollback)).
  Revisit this boundary when runtime selection or snapshot compatibility changes.

## Cold runtime installs and the per-instance cache

- **Kind**: latency and capacity constraint.
- **Boundary**: the first evaluation of a lock on an instance installs its runtime
  in the background and is refused with `SDD_RUNTIME_PREPARING` meanwhile. The
  cache is per instance, lives on `/tmp` (in-memory on Cloud Run) and is lost on
  restart. A cold install measured 11-18 seconds, a 29 MiB entry and a 153 MiB
  transient peak at cpu=1, 1 GiB in a local container, not on the serving host.
- **Consequence**: readiness after a scale-out, restart or lock change reports a
  retryable refusal, and a native run whose next head needs a cold install waits,
  keeping its state, until a later dispatcher tick finds the runtime installed or
  45 minutes pass and the run blocks with a remediation reason.
  Request-based CPU throttling can lengthen an
  install. Many distinct locks evict each other above `AUTOHUB_SDD_CACHE_BYTES`.
- **Treatment**: callers retry `SDD_RUNTIME_PREPARING`; operators size
  `AUTOHUB_SDD_CACHE_BYTES` against instance memory. Revisit with a shared cache
  when cold installs dominate evaluation latency or instances multiply.

## macOS isolation is development-only

- **Kind**: platform constraint.
- **Boundary**: macOS `sandbox-exec` cannot end detached processes that a
  sandboxed step leaves. Install steps use unguessable staging paths and Hub never
  acts below `.venv` after the first sandbox step, but a leftover process can keep
  running on the host.
- **Consequence**: macOS hosts do not give the containment that serving requires.
- **Treatment**: serve only from Linux hosts with bubblewrap; use macOS for local
  development and tests. Revisit if macOS serving becomes a requirement.

## Retained history and live deployment proof

- **Kind**: operational verification gap and retention constraint.
- **Boundary**: local checks and retained reports describe the source or deployment
  they actually observed. Detailed job/run history expires under
  `CAP-EXEC-scheduling-maintenance`; surviving summaries and external links are not
  a replayable record of every observation.
- **Consequence**: an old report cannot establish the currently serving revision,
  and expired database history can no longer explain every intermediate attempt.
- **Treatment**: bind deployment claims to recorded image/source identity and the
  relevant live checks. Preserve only evidence needed for active compatibility or
  deployment claims in [verification materials](../materials/index.md). Revisit
  the needed evidence after changing images, migrations, runtime models, credentials or
  provider behavior, and before relying on records outside their retention scope.

## Installation-wide account access

- **Kind**: product scope constraint, not automatically technical debt.
- **Boundary**: approved human accounts can operate Hub projects across the
  installation. Managed machine scopes select operation surfaces, not repository
  memberships. The host has no per-project account ACL.
- **Consequence**: adding an operator or issuing a scoped key cannot isolate it
  to a selected repository through an undocumented membership mechanism.
- **Treatment**: provision accounts and keys for the installation-wide access
  described by `CAP-ACCESS-authentication-authorization` and `CAP-MCP-tool-access`.
  Reconsider this scope only if the product must host operators or clients that
  cannot share those repository boundaries.

## External trigger dependency

- **Kind**: operational liveness dependency.
- **Boundary**: Hub has no resident scheduler timer. Due work and shared
  maintenance need external ticks; a running HTTP service alone does not advance
  them. Trigger-stopped notices depend on other incoming traffic.
- **Consequence**: pending cleanup, provider collection and retention can stop
  while ordinary HTTP health remains available.
- **Treatment**: inspect scheduler health and the actual external trigger under
  `CAP-EXEC-scheduling-maintenance` and `CAP-NOTIFY-operator-notifications`.
  Revisit provisioning and live evidence when the trigger, hosting request model
  or maintenance execution boundary changes.

## Source and evidence anchors

- `ARCH-06-execution` describes the source owners; capability IDs above own exact
  protocols and enforcement references.
- [Jules session service](../../modules/hub/app/features/execution/tasks/domains/jules/service.py)
  separates create-response application, unfinished-session collection and adoption.
- [Jules session tests](../../modules/hub/tests/integration/features/ai_catalogs/test_jules_sessions.py)
  provide controlled completion/reconciliation examples; they do not establish a
  live provider's create-response behavior.
- [Flow concurrency tests](../../modules/hub/tests/integration/features/execution/flows/test_host.py)
  and [publication tests](../../modules/hub/tests/integration/features/project_management/sdd/test_plan_publication.py)
  mark the PostgreSQL-only contention cases.
- [Dispatcher housekeeping](../../modules/hub/app/features/execution/dispatchers/usecases/housekeeping.py)
  and [housekeeping tests](../../modules/hub/tests/integration/features/notifications/test_tick_housekeeping.py)
  anchor trigger visibility and the limits of notification-driven observation.

These are source/test-inspected boundaries, not new executions, incident claims
or proof of Auto Hub's own SDD baseline.
