---
id: ADR-repository-locked-runtime
title: Evaluate SDD with the repository-locked runtime
summary: For SDD evaluation of any devkit-adopted repository, we install devkit from the evaluated commit's own uv.lock instead of server profiles, to remove per-repository provisioning and evaluate with the agents' runtime, accepting install cost and trust in the lock.
proposal: SPEC-repo-locked-sdd-runtime
status: superseded
superseded_by: ADR-repository-owned-sdd-execution
created_at: 2026-11-13
---

# [ADR-repository-locked-runtime] Evaluate SDD with the repository-locked runtime

Superseded in part by `ADR-repository-owned-sdd-execution`: all in-force decisions assigning runtime selection, installation and evaluation to Hub.

Superseded in part by `ADR-repository-path-sources`: the clause that the runtime identity is the digest of the uv export of that group plus the interpreter minor version.

- **Status**: Superseded by `ADR-repository-owned-sdd-execution`
- **Date**: 2026-11-13

---

## 1. Context & Problem Statement

Native SDD evaluation restores a checkout's managed assets with `devkit sync --locked`, which needs the package
of every bundle the committed receipt records. Runtimes are server-provisioned profiles selected by
`AUTOHUB_SDD_PROFILES`, and target dependencies are never installed. A repository whose receipt records a bundle
outside the reviewed profiles (for example `devkit-catalog` or `g-tools` bundles) is refused with
`SDD_BUNDLES_MISSING` until an operator adds a profile, changes the image and redeploys. Hub's devkit can also
differ from the one the agents used, which `RECEIPT_STALE` and `RUNTIME_REVISION_MISMATCH` only report.

## 2. Decision Drivers

- Any devkit-adopted repository is evaluable without operator provisioning.
- Hub evaluates with the same workflow, rule and bundle versions as the agents.
- Admitted runs keep a stable, checkable identity.
- Repository code still never runs with Hub credentials or network during evaluation.

## 3. Considered Options

1. Keep server profiles and add one per repository bundle set: no new trust, but provisioning and redeploys per repository.
2. Install from the base branch lock only: reviewed content, but evaluation can lag the head the agents used.
3. Install from the evaluated commit's own lock: no provisioning and runtime parity, trusting the repository's committed lock.

## 4. Decision Outcome

Chosen option: 3, because it is the only option that meets both the provisioning and the parity drivers; the user
accepted the risk that a pull request changes its lock to steer its own evaluation.

- The evaluation runtime is installed from the evaluated commit's root `uv.lock`: the locked dependency group that declares `devkit-spec`, rendered by uv. → `CAP-SDD-runtime-isolation` rules 1-2 (MUST)
- The commit is the base for activity start admission, the pull request head for inspection, decisions and final lint, the milestone ref for previews and batches, and the operator checkout for the SDK bridge. → `CAP-SDD-runtime-isolation` rule 1 (MUST)
- The runtime identity is the digest of the uv export of that group plus the interpreter minor version. → `CAP-SDD-runtime-isolation` rule 2 (MUST)
- A changed runtime identity on a later head continues with the new runtime; effective workflow, policy and configuration digests keep their refusal. → `CAP-SDD-runtime-isolation` rules 20-21 (MUST)
- A repository whose root lock lacks `devkit-spec` is refused with a repository diagnostic; no server profile or default image runtime remains. → `CAP-SDD-runtime-isolation` rule 3 (MUST)
- Installation runs outside request budgets, single-flight per digest across processes, and callers receive a retryable preparing diagnostic meanwhile. → `CAP-SDD-runtime-isolation` rules 6-7 (MUST)

## 5. Consequences

- Positive: onboarding a devkit repository needs no image or configuration change; revision-mismatch warnings disappear by construction.
- Negative: the first evaluation per lock and instance waits for an install; the cache costs memory on Cloud Run's in-memory filesystem.
- Risk: a lock change can alter the rules that judge its own pull request; accepted by the user.
- Follow-up: runs, batches and bridge claims admitted under server pins are settled before rollout and again on rollback.

## 6. Confirmation

Tests planned in the handed-off spec for identity per path, refusal of lockless repositories, continuation on a
changed identity and concurrent cold installs; review of the restating capability revision.
