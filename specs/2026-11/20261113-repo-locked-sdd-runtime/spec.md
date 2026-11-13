---
id: SPEC-repo-locked-sdd-runtime
title: Install the SDD evaluation runtime from the repository lock
summary: Auto Hub evaluates SDD work with the devkit packages pinned by the target repository's uv.lock, installed inside isolation, instead of a server profile that must contain every selected bundle. This removes per-repository provisioning.
status: in-progress
created: 2026-11-13
related_capabilities:
  - CAP-SDD-runtime-isolation
  - CAP-SDD-native-delivery
  - CAP-SDK-existing-pr-bridge
related_usecases:
  - UC-start-sdd-activity
  - UC-complete-sdd-workflow
  - UC-execute-sdd-batch
workflow: sdd-spec-feature
---

# [SPEC-repo-locked-sdd-runtime] Install the SDD evaluation runtime from the repository lock

## 1. Problem Statement & Motivation

Handed off from proposal PROP-repo-locked-sdd-runtime on 2026-11-13. The decisions are recorded in
`ADR-repository-locked-runtime` and `ADR-offline-source-build`.

Native SDD evaluation runs devkit from server-provisioned runtime profiles (`AUTOHUB_SDD_HOME`,
`AUTOHUB_SDD_PROFILES`, `config/sdd-runtime*`) and never installs target repository dependencies
(`CAP-SDD-runtime-isolation`). Restoring a checkout's managed assets needs the package of every bundle the
committed receipt records, so a repository whose receipt names a bundle outside the reviewed profiles is refused
with `SDD_BUNDLES_MISSING` until an operator adds a profile, changes the image and redeploys. Hub's devkit can also
differ from the devkit the agents used.

This spec replaces server profiles with a runtime installed from the evaluated commit's own `uv.lock`, keeps
repository code away from credentials and network, and makes the install independent of request budgets.

## 2. User Stories

- As a project operator, I connect any devkit-adopted repository and Hub evaluates its SDD work without an image
  change, profile mapping or redeploy (`UC-start-sdd-activity`, `UC-complete-sdd-workflow`).
- As a project operator, I see evaluation use the same devkit, workflow and rule versions the agents installed from
  the repository lock.
- As a project operator, a devkit bump inside an admitted run does not force re-enrollment while the effective
  workflow, policy and configuration stay the same.
- As an operator of the serving host, no repository build code can read Hub credentials or reach the network.
- As a batch operator, batch evidence compares a deterministic runtime identity (`UC-execute-sdd-batch`).

## 3. Non-Goals

**Scope Excluded**

- Installing a repository's whole environment: only the locked dependency group that declares `devkit-spec` (or
  the main dependencies when declared there) is installed.
- Downloading Python interpreters on demand; the image interpreter is the only one.
- Git sources outside `https://github.com/`, path, URL or editable sources, and package indexes other than the
  default PyPI index.
- Building registry sdists: registry packages must provide wheels.
- A cache shared across instances or surviving restarts (for example Cloud Storage).
- Changing the Cloud Run CPU allocation or memory settings; operations guidance only.
- A fallback server runtime for repositories without a devkit lock.

**When to Reconsider**: a consumer that needs another Git host, a private index or a registry sdist.

## 4. Acceptance Criteria & Behavioral Contracts

Identity, diagnostics and paths named here are the contract `CAP-SDD-runtime-isolation` restates after this spec.
The runtime identity is the SHA-256 of a JSON document holding the `uv export --frozen --no-header --no-annotate`
text of the selected group, the image interpreter's `major.minor` and the build environment's lock digest. The CLI
identity stored in snapshots is `devkit-lock:<identity>`.

### [AC-01] Evaluate with the runtime of the evaluated commit's lock

- **Given** a repository whose root `pyproject.toml` declares `devkit-spec` in a dependency group, whose `uv.lock`
  is committed, and a cache entry complete for that lock's identity
- **When** readiness inspects a pull request head
- **Then** every devkit command runs with `<cache>/<identity>/.venv/bin/python`, the response is HTTP 200 and the
  stored snapshot's `cli_version` equals `devkit-lock:<identity>`; `AUTOHUB_SDD_PROFILES` is never read.

### [AC-02] Bundles come from the repository lock

- **Given** a receipt that records a bundle provided by a package in the selected group
- **When** the head is evaluated
- **Then** managed assets are restored without `SDD_BUNDLES_MISSING`.
- **Given** a receipt or preset that requires a bundle no installed package provides
- **When** the head is evaluated
- **Then** Hub refuses with HTTP 422, code `SDD_BUNDLES_MISSING`, diagnostic category `repository`, before sync.

### [AC-03] Unrelated lock changes keep the identity

- **Given** two commits whose locks differ only in a package outside the selected group
- **When** each commit's identity is computed
- **Then** both identities are equal; a change of a package inside the group yields a different identity.

### [AC-04] A changed identity on a later head continues

- **Given** an admitted run whose snapshot `cli_version` names identity X and a later head whose lock resolves
  identity Y, with unchanged effective workflow, policy and configuration
- **When** the run is evaluated
- **Then** evaluation proceeds without the "SDD CLI version differs from the execution pin" refusal and the new
  snapshot records `devkit-lock:Y`; a changed effective workflow still refuses continuation.

### [AC-05] Repositories without a devkit lock are refused

- **Given** a commit without a root `uv.lock`, or whose root `pyproject.toml` declares `devkit-spec` in no
  dependency group and no main dependency
- **When** any devkit command is requested for it
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_UNLOCKED`, diagnostic category `repository`, retry
  `after_fix`, and starts no install.

### [AC-06] Unsupported sources are refused before any network access

- **Given** a selected group whose export contains a path, URL or editable requirement, a Git source outside
  `https://github.com/`, or an index option
- **When** the runtime is resolved
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_SOURCE_UNSUPPORTED`, and performs no fetch or download.

### [AC-07] An incompatible Python requirement is refused

- **Given** a root `requires-python` that excludes the image interpreter's version
- **When** the runtime is resolved
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_PYTHON_UNSUPPORTED`, and starts no install.

### [AC-08] A cold cache prepares once and reports a retryable state

- **Given** no complete cache entry for an identity and two worker processes receiving five concurrent
  evaluations for it
- **When** they request devkit commands
- **Then** exactly one install runs for that identity, every caller that cannot use the entry yet receives HTTP 503,
  code `SDD_RUNTIME_PREPARING`, retry `safe`, and after the install completes the next evaluation proceeds as in
  AC-01.

### [AC-09] A caller's deadline does not cancel the install

- **Given** an install for an identity in progress
- **When** the caller's request deadline expires
- **Then** the install continues to completion, the entry becomes complete with its `pin.json`, and no partial
  directory is left at the entry path.

### [AC-10] Build code never sees credentials or the network

- **Given** a selected group with Git sources
- **When** the runtime is installed
- **Then** Git sources are fetched in the Hub process with the project's GitHub connector token; every build
  command runs in the OS sandbox with network unshared and an environment of only `PATH`, `HOME`, `TMPDIR`,
  `LANG` and uv offline settings; the token appears in no build argument, build environment, `pin.json` or
  diagnostic; and a build hook that opens a network connection fails.

### [AC-11] An unreadable Git source is reported without upstream text

- **Given** a locked Git source the connector token cannot read
- **When** the runtime is installed
- **Then** the entry stays incomplete and later callers receive HTTP 422, code `SDD_RUNTIME_SOURCE_UNAVAILABLE`,
  with a Hub-authored message that names no URL, token or Git stderr; a retry is allowed after the fix.

### [AC-12] Git-only operations never wait for a runtime

- **Given** a cold cache for the base commit's identity
- **When** an activity start creates its branch through `git-safe` commands only
- **Then** the branch is created and no install is started.

### [AC-13] Eviction never removes a runtime in use

- **Given** cache entries whose total size exceeds `AUTOHUB_SDD_CACHE_BYTES`, one of them leased by a running
  evaluation
- **When** eviction runs
- **Then** least-recently-used unleased entries are removed until the total fits or only leased entries remain, and
  the leased entry stays intact.

### [AC-14] Host and project runtime probes are separate

- **Given** a serving host
- **When** `GET /api/v1/projects/{project_id}/sdd/runtime` is requested
- **Then** the response reports the host probe (`isolation`, `ok`) from an interpreter started inside the sandbox
  without installing anything, and the project lock state `state` = `ready`, `preparing` or `failed` with
  `identity`, `bundles` and `revisions` when known; `profile` is `repository-lock`.

### [AC-15] Batch evidence compares a deterministic identity

- **Given** the same commit evaluated through two different cache directories
- **When** batch basis evidence is captured
- **Then** both `runtime` values are equal and contain only `provider`, `identity`, `python` and `revisions`; the
  basis no longer hashes the whole `uv.lock`.

### [AC-16] The existing-PR bridge uses its checkout's lock

- **Given** an SDK bridge target with an operator checkout whose lock declares devkit
- **When** the bridge reads evidence
- **Then** the runtime identity comes from that checkout's lock and the evidence digest covers the snapshot's
  `devkit-lock:<identity>`.

### [AC-17] Retired codes stay readable

- **Given** a retained run record with a `RUNTIME_REVISION_MISMATCH` warning
- **When** its diagnostics are projected
- **Then** the catalog message is shown; new evaluations never emit that code.

### [AC-18] Cold-install cost is measured

- **Given** the g-scavenger-crew lock and the serving image shape (cpu=1, 1Gi)
- **When** a cold install is run
- **Then** the elapsed seconds and the entry plus transient cache size in MiB are recorded under this spec's
  `materials/`, and the default `AUTOHUB_SDD_CACHE_BYTES` is set from that measurement.

## 5. Security

- Repository build and evaluation code runs only inside the OS sandbox, with no network and no credentials.
- The connector token is used only by Hub-process Git fetches, through the same credential mechanism as checkout.
- Registry artifacts are wheels installed with hash verification; installing a wheel executes no package code.
- Diagnostics remain Hub-authored catalog text (`CAP-SDD-runtime-isolation` rule 14).

## 6. Assumptions

- Hatchling is the only build backend the supported Git sources need; the image's build environment pins it.
- The serving host can reach PyPI and GitHub from the Hub process.
- Cloud Run CPU throttling slows a background install between requests but does not stop it; scheduled dispatcher
  requests resume progress.
- Settling active native runs, open batch selections and approved bridge claims before rollout is an operator
  procedure, not code.
- Cache entries are content-addressed and shared by all projects of an instance that lock the same runtime; one
  operator owns every project of an instance. Install failure markers are scoped to the credential that failed.
