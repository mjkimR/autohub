---
id: PROP-repo-locked-sdd-runtime
title: Install the SDD evaluation runtime from the repository lock
summary: Auto Hub evaluates SDD work with the devkit packages pinned by the target repository's uv.lock, installed inside isolation, instead of a server profile that must contain every selected bundle. This removes per-repository provisioning.
status: reviewing                       # draft | reviewing | accepted | rejected
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

Code facts this design rests on (head of this branch):

- Every devkit call runs `<home>/.venv/bin/python -m devkit_dist` inside
  bubblewrap/sandbox-exec with the checkout writable, `<home>` read-only and no
  network (`isolation.py`). `<home>` comes from the selected profile
  (`profiles.py`) and its `pin.json` (written by `scripts/install-sdd.py`).
- Run identity is `cli_version = "devkit-spec:" + pin.lock_sha256`; a snapshot
  whose `cli_version` differs refuses evaluation ("SDD CLI version differs from
  the execution pin", `services.py`).
- Every devkit command has a 25-second timeout (`checkout.py`); the checkout is
  fetched with the project's GitHub connector token, which never enters the sandbox.
- The SDK bridge selects the runtime with the same `runtime_scope(repository)`
  (`execution/flows/bridge.py`).

Design after challenger round 01 (`envelopes/challenger-01.yaml`). Items marked
**(open)** wait for the user's answers under Open decisions below.

- **D1 Source and resolution point**: the runtime is resolved after fetch, per
  evaluated commit, from its root `pyproject.toml` and `uv.lock` (parsed, never
  executed, in the Hub process). `checkout()` no longer selects a runtime on
  entry. Paths and the commit whose lock they use:

  | Path | Commit |
  | --- | --- |
  | Activity start admission (`policy.py` start_blocker) | base |
  | Inspect, readiness, enrollment, decisions, final lint | PR head |
  | Milestone preview and batch evidence | resolved milestone ref |
  | SDK existing-PR bridge | operator checkout HEAD |

- **D2 Install set**: the locked dependency group(s) of the root project that
  declare `devkit-spec` (or the main dependencies when declared there),
  rendered by uv itself with `uv sync --frozen --only-group <group>
  --no-install-project` into the target venv. This covers every bundle package
  the committed presets can select, including the `RECEIPT_STALE`
  regeneration path, and leaves markers, forks and hashes to uv. The rest of
  the repository's environment is never installed. A missing bundle after
  install is a repository lock defect (`SDD_BUNDLES_MISSING`, now checked
  against the installed entry points).
- **D3 Identity**: the runtime identity is the SHA-256 of `uv export --frozen`
  for that group plus the interpreter's minor version: a deterministic,
  identity-only pin schema (no cache path, timestamps or ordering). Batch
  evidence stores this identity instead of the whole `runtime_pin()` and its
  `uv.lock` configuration hash narrows to the same digest. Whether a changed
  identity on a later head refuses continuation is **(open, Q-A)**.
- **D4 Install isolation and sources** **(open, Q-B)**: the install runs in the
  OS sandbox with a writable venv and uv cache, only the manifest and lock
  visible, `/etc/resolv.conf` and CA certificates bound read-only, and a pinned
  `uv` copied into the runtime image stage. Evaluation is unchanged: no
  network, no credentials, venv read-only. How private Git sources are fetched
  and whether build backends run with network egress is the open decision.
- **D5 Install lifecycle and cache**: installation is decoupled from request
  budgets. A per-digest cross-process file lock (`fcntl`) makes one build per
  instance; an existing complete target counts as success. The build runs to
  completion in the background even when the caller's deadline expires;
  callers meanwhile receive a retryable `SDD_RUNTIME_PREPARING` diagnostic
  (`retry: safe`). Builds go to a temporary directory renamed into place with
  `pin.json`. Eviction is lease-protected (never a venv an evaluation holds)
  under an explicit byte cap; the uv cache is pruned after each install.
  git-safe commands no longer use the devkit venv: they run in isolation with
  the image's Git only, so branch creation and decision commits never wait for
  a runtime install.
- **D6 Python**: the image's interpreter (3.13) when the repository's
  `requires-python` admits it; otherwise refuse with a repository diagnostic.
  No on-demand interpreter downloads.
- **D7 Retirement and probe**: remove `AUTOHUB_SDD_PROFILES`,
  `config/sdd-runtime-app-common` and repository mapping. Whether a default
  image runtime remains as a fallback for repositories without a devkit lock is
  **(open, Q-C)**. Stop emitting `RUNTIME_REVISION_MISMATCH` (identical by
  construction) but keep its diagnostic catalog entry for historical records.
  Keep the `RECEIPT_STALE` regeneration exception. Split the runtime status
  probe: a host isolation probe (image interpreter and Git in the sandbox, no
  repository, no install) keeps rule 15; a separate project-lock probe reports
  `preparing`, `ready` or a lock diagnostic.
- **D8 Migration and rollback**: before rollout the operator settles active
  native runs, open batch selections and approved but unresumed SDK bridge
  claims; their stored identities refer to the server pin and are refused
  afterward. Rolling back the deployment likewise strands runs enrolled under
  lock-derived identities, so a rollback repeats the settlement. The live
  canary `mjkimR/test-sandbox` has no `.devkit/` or `uv.lock` (checked through
  the GitHub API on 2026-11-13), so it is not an SDD consumer today.
- **Acceptance evidence to plan**: a measured cold-install time and venv plus
  cache size for the g-scavenger-crew lock on the Cloud Run shape (cpu=1,
  1Gi), which sets the byte cap and `--memory`; a forked or marker-gated
  fixture lock; concurrent cold requests across worker processes.

- Contracts affected: `CAP-SDD-runtime-isolation` (scope exclusion, rules 1-4,
  6, 9, 10, 11, 15), `CAP-SDK-existing-pr-bridge` profile selection,
  `ARCH-07-deployment`, `ARCH-11-risks-and-technical-debt` and the operations
  guides for the SDD runtime and execution targets.

### Open decisions for plan-accept

- **Q-A (identity on a changed head)**: when a later head of an admitted run
  resolves a different runtime identity (a devkit bump, or a base merge that
  changed it), either keep rule 9's refusal and require re-enrollment, or treat
  the repository's committed lock as authority: continue with the new runtime
  while the effective workflow, policy and configuration digests keep their
  existing refusal. Recommendation: continue; those digests already detect
  every contract change the runtime pin was guarding.
- **Q-B (install trust and credentials)**: git sources such as devkit and
  g-tools ship no wheels, so installing them runs build-backend code. Options:
  (1) run the install in the sandbox with network egress and a dedicated
  read-only source token; (2) fetch Git sources in the Hub process with the
  project's GitHub connector token (as `checkout()` already does), then install
  in the sandbox with no credentials, build steps without network using build
  backends pinned in the image, and network only for registry artifact
  downloads. Whether uv can separate download from build this way is a
  Development check; if not, the fallback is an offline install from artifacts
  the Hub process downloads. Option 1 exposes the token and the Cloud Run
  metadata server (service-account token) to build code and needs the token
  granted on every new private source. Recommendation: option 2.
- **Q-C (repositories without a devkit lock)**: keep a default image runtime
  as a fallback for repositories whose root lock has no `devkit-spec`, or
  refuse them with a repository diagnostic. Recommendation: refuse; no known
  consumer relies on a lockless setup, and one runtime source keeps identity
  simple.

## 4. Lifecycle & Retirement Criteria

- On Acceptance: recorded with devkit spec proposal accept (after Planning, or --direct for an eligible draft in Backlog); handed off to a spec bundle on dev-<slug>; the proposal is deleted there and its decisions become ADRs
- On Rejection: status: rejected only, with the user's reason in the commit message; a later hygiene pass writes the rejection ADR and deletes the proposal
