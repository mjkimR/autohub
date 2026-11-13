---
id: PROP-repo-locked-sdd-runtime
title: Install the SDD evaluation runtime from the repository lock
summary: Auto Hub evaluates SDD work with the devkit packages pinned by the target repository's uv.lock, installed inside isolation, instead of a server profile that must contain every selected bundle. This removes per-repository provisioning.
status: draft                         # draft | reviewing | accepted | rejected
created_at: 2026-11-13
target_area: capabilities/sdd/
priority: high                        # critical | high | medium | low
size: L                               # S | M | L | XL (XL: would need two or more specs or task kinds; decompose before Planning)
planning_effort: medium               # low | medium | high (hint for Planning)
dev_effort: medium                    # low | medium | high (hint for Development)
boundaries:
  owns:
    - capabilities/sdd/
    - architecture/
    - operations/
  excludes:
    - docs/decisions/
task_kind: feature                    # feature | bugfix: the spec follows sdd-spec-<task_kind>
workflow: sdd-proposal
---

# [PROP-repo-locked-sdd-runtime] Install the SDD evaluation runtime from the repository lock

## 1. Background & Hypothesis

Native SDD evaluation runs devkit from a server-provisioned runtime profile
(`AUTOHUB_SDD_HOME`, `AUTOHUB_SDD_PROFILES`, `config/sdd-runtime*`) and never
installs target repository dependencies (`CAP-SDD-runtime-isolation`, Scope
Excluded and rule 4). Before evaluating, Hub restores the Git-ignored managed
assets with `devkit sync --locked`, which needs the package of every bundle the
committed receipt records. A profile lacking one refuses with
`SDD_BUNDLES_MISSING`.

Onboarding a Godot repository for a pilot exposed the cost: its receipt records
`deep-research` and `response-style` (from `devkit-catalog`) and `g-foundation`
(from `g-tools`). The first two provide only agent skills and guidance that Hub
never evaluates, yet they block restoration; the last supplies a rule that final
lint really runs. Every such repository needs a new reviewed profile, a
Dockerfile change, a serving-configuration mapping and a redeploy before its
first run. Hub's evaluator can also differ from the devkit the agents installed,
which the `RECEIPT_STALE` and `RUNTIME_REVISION_MISMATCH` paths only warn about.

Decision taken at intake (user): trust the target repository's committed lock.
A lock changed to steer its own evaluation is judged unlikely; dependency
friction is the larger problem.

Hypothesis: installing the devkit packages from the evaluated commit's `uv.lock`
inside isolation, cached by lock digest, makes any devkit-adopted repository
evaluable without operator provisioning, and makes Hub evaluate with the same
workflow, rule and bundle versions the agents used.

## 2. Technical Spike Questions

- **Q1 (identity)**: Rule 9 pins runtime identity for an admitted run. When the
  runtime derives from the evaluated commit's lock, which lock defines a run's
  identity, and what happens when a PR changes it mid-run: refuse continuation,
  re-admit, or treat it as an authorized transition?
- **Q2 (install scope)**: Install the whole locked dev environment
  (`uv sync --frozen`) or only devkit-related packages selected from the lock?
  How is a lock without devkit, or with devkit installed some other way, handled?
- **Q3 (cache and cost)**: Where does a lock-digest venv cache live on Cloud Run
  (ephemeral disk, per-instance), and what install latency and size are
  acceptable for readiness, start and decision evaluation?
- **Q4 (network and credentials)**: The install step needs network and read
  access to private Git sources (devkit, g-foundation), while evaluation stays
  without network. Which credential is passed, how is it kept out of the
  evaluation sandbox and diagnostics, and which source hosts are allowed?
- **Q5 (Python)**: Which interpreter satisfies the repository's
  `requires-python`: uv-managed Python downloaded on demand, or a fixed set in
  the image?
- **Q6 (retirement)**: What happens to `AUTOHUB_SDD_PROFILES`, `check_bundles`,
  the `RECEIPT_STALE` regeneration exception, `RUNTIME_REVISION_MISMATCH`, the
  runtime status endpoint and the SDK existing-PR bridge, which shares profile
  selection? Is the server profile kept as a fallback or removed?

## 3. Proposed Design & Impact

To be settled in Planning. Initial direction:

- A two-phase isolated runner: an install phase with network limited to the
  needed package sources and a scoped read credential, producing a read-only
  venv keyed by the lock's digest; then the existing evaluation phase with no
  network and no credentials, using that venv's devkit.
- Runtime identity becomes the installed lock digest instead of the server pin.
- Contracts affected: `CAP-SDD-runtime-isolation` (scope exclusion, rules 1-4,
  6, 9, 10, 11, 15), `CAP-SDK-existing-pr-bridge` profile selection,
  `ARCH-07-deployment`, `ARCH-11-risks-and-technical-debt` and the operations
  guides for the SDD runtime and execution targets.

## 4. Lifecycle & Retirement Criteria

- On Acceptance: recorded with devkit spec proposal accept (after Planning, or --direct for an eligible draft in Backlog); handed off to a spec bundle on dev-<slug>; the proposal is deleted there and its decisions become ADRs
- On Rejection: status: rejected only, with the user's reason in the commit message; a later hygiene pass writes the rejection ADR and deletes the proposal
