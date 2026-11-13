---
id: SPEC-repo-path-runtime-sources
title: Install repository-local path sources in the SDD runtime
summary: SDD runtime selection accepts dependency-group path and editable sources that resolve inside the evaluated checkout, so in-repository and snapshot bundles install like Git sources instead of being refused.
status: planned
created: 2026-11-13
related_capabilities:
  - CAP-SDD-runtime-isolation
related_usecases:
  - UC-start-sdd-activity
  - UC-complete-sdd-workflow
workflow: sdd-spec-feature
---

# [SPEC-repo-path-runtime-sources] Install repository-local path sources in the SDD runtime

## 1. Problem Statement & Motivation

Agreed intent (user): repositories install their own devkit bundles, developed in the repository or copied with
`devkit bundle snapshot` (devkit ADR-bundle-source-snapshots), as editable path packages in the dev dependency group
(devkit CAP-DIST-in-repo-bundles). Auto Hub's lock-derived SDD runtime (`SPEC-repo-locked-sdd-runtime`,
`CAP-SDD-runtime-isolation`) refuses every path or editable requirement with `SDD_RUNTIME_SOURCE_UNSUPPORTED`, so any
repository with an in-repository bundle cannot be evaluated. Accept path and editable sources that resolve inside the
evaluated checkout, build and install them like locked Git sources (sandboxed, offline), and include their content in
the runtime identity. Paths outside the checkout stay refused.

uv renders such sources in the selected group's export as `-e ./<path>` (editable) or `./<path>` (non-editable);
a source outside the checkout renders as `../<path>` or an absolute path. The export needs only the root
`pyproject.toml` and `uv.lock`, so selection still renders it in a temporary directory; the source trees are read
from the checkout itself. Rule 4 of `CAP-SDD-runtime-isolation` and the identity clause of
`ADR-repository-locked-runtime` change, so a new ADR is required before implementation.

## 2. User Stories

- **US-1**: As a project operator, I connect a repository whose devkit group locks an in-repository or snapshot
  bundle as a path source, and Hub evaluates its SDD work without an image change (`UC-start-sdd-activity`,
  `UC-complete-sdd-workflow`).
- **US-2**: As a project operator, a commit that changes an in-repository bundle is evaluated with a runtime built
  from that commit's bundle content, not a cached runtime of earlier content.
- **US-3**: As an operator of the serving host, a path source can neither read files outside the evaluated checkout
  nor run build code with credentials or network.

## 3. Non-Goals

1. **Scope Excluded**: path sources outside the evaluated checkout (`../` or absolute paths), path sources that are
   archives (wheel or sdist files, `name @ file://...`) and URL sources stay refused.
2. **Scope Excluded**: symbolic links inside a path source tree or on its path; such a source is refused, not
   followed or skipped. **When to Reconsider**: a consumer bundle that needs a symlink to a file inside its own
   tree.
3. **Scope Excluded**: editable installs in the runtime. A path source is installed as a built wheel; the runtime
   is disposable and rebuilt when the identity changes.
4. **Scope Excluded**: path requirements with environment markers, and build backends other than the image's
   pinned hatchling environment.
5. **Scope Excluded**: locks whose export needs manifests other than the root `pyproject.toml` and `uv.lock`
   (for example uv workspace members); they keep their current `SDD_RUNTIME_UNLOCKED` result.
6. **Scope Excluded**: new `pin.json`, runtime status, batch evidence or UI fields; the path content reaches them
   only through the runtime identity.

## 4. Acceptance Criteria & Behavioral Contracts

The fixture used below is a repository whose dev group locks devkit from GitHub plus `my-bundle` as
`{ path = "tools/my-bundle", editable = true }` and `plain-bundle` as `{ path = "tools/plain" }`, with both
directories committed.

### [AC-01] In-checkout path and editable sources are selected

- **Given** the fixture, whose group export contains `-e ./tools/my-bundle` and `./tools/plain`
- **When** the runtime is selected
- **Then** selection succeeds with exactly two path sources, `my-bundle` at `tools/my-bundle` and `plain-bundle`
  at `tools/plain`, the same Git and registry sources as without them, and no `SDD_RUNTIME_SOURCE_UNSUPPORTED`
  refusal.
- **Given** a repository whose only `devkit-spec` source is an in-checkout path source
- **When** the runtime is selected
- **Then** selection succeeds and `devkit-spec` counts as the locked devkit package.

### [AC-02] The runtime identity covers path source content

- **Given** the fixture checked out in two different directories
- **When** each identity is computed
- **Then** both identities are equal.
- **Given** a second checkout that changes one byte of one file, or the executable bit of one file, under
  `tools/my-bundle`
- **When** its identity is computed
- **Then** it differs from the first checkout's identity.
- **Given** a lock without path sources
- **When** its identity is computed
- **Then** it equals the SHA-256 of the sorted-key JSON `{"build", "export", "python"}` document defined before this
  spec, so existing cache entries and recorded `devkit-lock:<identity>` values stay valid.

### [AC-03] Path sources outside the checkout or unsafe trees are refused

- **Given** a selected export whose path source is `../ext`, an absolute path, a path through a symlinked
  directory, a missing directory, a directory without a regular `pyproject.toml`, or a tree that contains a
  symlink or a non-regular file
- **When** the runtime is selected
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_SOURCE_UNSUPPORTED`, reads no file outside the checkout and
  starts no install.
- **Given** a path requirement with a `--hash` option or an environment marker, or a `name @ file://` requirement
- **When** the export is classified
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_SOURCE_UNSUPPORTED`.

### [AC-04] Path source size is bounded

- **Given** path sources of one selection holding more than 10,000 files or more than 32 MiB of file content in
  total, excluding `.git`, `.venv` and `__pycache__` directories
- **When** the runtime is selected
- **Then** Hub refuses with HTTP 422, code `SDD_RUNTIME_SOURCE_UNSUPPORTED`, with Hub-authored text naming both
  limits.

### [AC-05] Path sources install without credentials or network

- **Given** a selection with path sources and Git sources
- **When** the runtime is installed
- **Then** the Hub process writes each path source's selected content under `work/src/` without a fetch, each path
  source is built with `uv build --wheel --offline --no-build-isolation` in the sandbox that writes only `work/`,
  the built wheels are installed by the sandboxed `.venv` step, and the connector token appears in no step for a
  path source.
- **Given** a repository whose `devkit-spec` and bundle are in-checkout path sources, and no network
- **When** the runtime is installed through the real sandbox
- **Then** the entry becomes complete with a `pin.json` whose `bundles` include the path bundle's entry point.

### [AC-06] The install uses the content captured at selection

- **Given** a selection made from a checkout whose directory is removed before the background install runs
- **When** the runtime is installed
- **Then** the install succeeds from the content captured at selection, and the staged tree's digest equals the
  digest in the identity.

## 5. Security

- Path source trees are read only by the Hub process at selection, without following symlinks, and only below the
  checkout root; no repository code runs there.
- Path source builds run in the same sandbox as Git source builds: no network, no credentials, one writable
  directory, the image's pinned backend.
- Refusals remain Hub-authored catalog text (`CAP-SDD-runtime-isolation` rule 25).

## 6. Assumptions

- uv renders in-checkout path sources as `./<relative path>`, with `-e ` for editable sources, and names the
  package for that path in the lock as `source = { editable = "<path>" }` or `{ directory = "<path>" }`; verified
  with `uv lock --offline` and `uv export --frozen --offline` on a fixture.
- A fresh Hub checkout contains only tracked files, so the tree digest is the same on every instance for the same
  commit; `.git`, `.venv` and `__pycache__` directories are excluded so an operator checkout (SDK bridge) does not
  add interpreter caches.
- The 10,000-file and 32 MiB bounds exceed in-repository bundles by a wide margin; the captured content stays in
  memory only while selection and its install run.
- A path source location uses only ASCII letters, digits, `.`, `_` and `-` in each component; other characters
  are refused. File names inside the tree are not restricted.
