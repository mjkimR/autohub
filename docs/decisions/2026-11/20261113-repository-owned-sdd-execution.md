---
id: ADR-repository-owned-sdd-execution
title: Keep repository SDD execution outside Hub
summary: "For connected-repository SDD work, we delegate setup and workflow execution to the repository and its agent, to keep Hub focused on PR orchestration, accepting failures discovered after dispatch."
proposal: SPEC-optimistic-sdd-orchestration
supersedes: [ADR-repository-locked-runtime, ADR-repository-path-sources, ADR-offline-source-build, ADR-sdd-batch-ledger]
status: accepted
created_at: 2026-11-13
---

# [ADR-repository-owned-sdd-execution] Keep repository SDD execution outside Hub

- **Status**: Accepted
- **Date**: 2026-11-13

## 1. Context & Problem Statement

Hub installs and executes each evaluated commit's devkit, restores generated
assets and derives the next permitted workflow stage. Admission, decisions,
batches and the existing-PR SDK bridge depend on that evaluation. This makes Hub
responsible for repository setup, tooling compatibility and internal workflow
correctness before it can request work.

Repository setup and SDD correctness belong to the repository and its working
agent. Hub already has a separate responsibility for PR dispatch, human input,
CI observation and merge policy. Installing another repository's development
tools is unnecessary for that responsibility.

## 2. Decision Drivers

- Start explicitly requested work without proving repository readiness first.
- Keep repository setup, internal gates and correctness with its agent and owner.
- Reuse PR questions, delivery identity and GitHub Actions observation.
- Remove runtime provisioning and controller complexity without a remote successor.
- Preserve historical evidence and prevent old authority from becoming new work.

## 3. Considered Options

1. Keep the embedded devkit evaluator: preserves stage guarantees but retains the
   repository responsibility and provisioning cost being removed.
2. Run the evaluator through GitHub Actions: removes local execution but adds
   dispatch/result recovery and keeps Hub responsible for repository readiness.
3. Dispatch work optimistically through the PR lifecycle: delegates repository
   execution to its agent, accepting that setup or workflow problems are found
   after work starts. Selected.

## 4. Decision Outcome

We select optimistic PR orchestration because it removes the repository
responsibility instead of relocating its evaluator.

- Hub forwards explicit unit/activity intent to the working agent without testing repository SDD readiness. → `CAP-SDD-native-delivery` rule 1 (MUST).
- Repository setup, asset management and workflow interpretation belong to the repository and its agent. Hub neither runs nor delegates `devkit sync` as a prerequisite or replacement service. → `CAP-SDD-native-delivery` rules 2–3 (MUST).
- Hub uses ordinary PR delivery, durable questions/answers and explicit resume; it does not select stages or author repository workflow decisions. → `CAP-PR-pull-request-delivery` SDD activity context (MUST).
- Both activity kinds start Draft. Existing PR ready state, current-head GitHub checks and project merge policy govern delivery; Hub claims no enforcement of repository-internal gates. → `CAP-SDD-native-delivery` rule 8 (MUST).
- Required repository verification executes in repository-owned GitHub Actions, whose results Hub observes through its existing CI contract. No Action or runner is introduced for devkit asset restoration or readiness evaluation. → `CAP-PR-pull-request-delivery` verification ownership (MUST).
- Executable milestone readiness, graph-based native batches and the evaluator-coupled SDK bridge bindings are retired without replacement execution systems. → `CAP-SDD-native-delivery` rule 9 and `CAP-SDK-existing-pr-bridge` rule 1 (MUST).
- Historical native evidence remains readable. Old execution authority is fenced and cannot implicitly convert into an optimistic Run. → `ARCH-06-execution` Legacy execution retirement (MUST).
- The serving image carries no SDD devkit runtime, installer, build environment or evaluation sandbox requirement. Auto Hub's contributor devkit process remains repository-owned tooling. → `ARCH-07-deployment` Deployment boundary (MUST).

Supersedes in part `ADR-repository-locked-runtime`: all in-force decisions assigning runtime selection, installation and evaluation to Hub.

Supersedes in part `ADR-repository-path-sources`: all decisions assigning path-source capture, identity and installation to Hub.

Supersedes in part `ADR-offline-source-build`: all decisions assigning source fetch, build and isolated evaluation to Hub.

Supersedes in part `ADR-sdd-batch-ledger`: all decisions defining live graph-based native SDD batch admission and progression.

This decision replaces all in-force decisions in `ADR-repository-locked-runtime`,
`ADR-repository-path-sources`, `ADR-offline-source-build` and
`ADR-sdd-batch-ledger`. Each is superseded. `ADR-sdd-development` remains accepted
because it governs Auto Hub's own contributor workflow.

The open-proposal inventory in `SPEC-optimistic-sdd-orchestration` has no proposal
whose sole outcome is embedded SDD evaluation. Keep unrelated outcomes; adjust
live native-control assumptions in `PROP-run-origin-links` and deleted-write
examples in `PROP-updated-at-maintenance`. This decision rejects the embedded
runtime/evaluator design, not those independent read/metadata improvements.

## 5. Consequences

Hub loses preflight and per-stage SDD guarantees. Invalid or incomplete repository
setup may consume an agent attempt before being reported. Operators use existing
question/resume and GitHub PR mechanisms instead of Hub's devkit-specific gates.

Milestone execution preview, automatic native batch admission and built-in SDK
SDD/PR bridge workflows are removed product surfaces. Their retained records
remain inspectable. Providing a different queue or bridge is outside this work.

Runtime caches, source builds, bundle compatibility and sandbox-host support no
longer affect activity admission. Repository-specific required checks remain in
GitHub Actions; this decision creates no verification workflow on their behalf.

## 6. Confirmation

`SPEC-optimistic-sdd-orchestration` AC-01 through AC-12 define the delivery checks.
Source regressions include optimistic activity/API and claim recovery, ordinary
question/PR progression, retirement migration, bridge refusal and generic flows,
plus UI absence-of-probe/history behavior. Source/import and serving-image review
verify evaluator removal. The spec's check records identify commands actually
executed; this decision does not establish live provider, GitHub or deployment
verification.
