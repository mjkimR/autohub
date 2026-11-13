---
id: ADR-repository-path-sources
title: Install repository path sources from the evaluated checkout
summary: "For repositories that lock in-repository devkit bundles as path sources, we copy each source inside the checkout in the Hub process, build it offline in the sandbox and hash its content into the runtime identity, to evaluate them like Git sources, accepting bounded per-selection reads."
status: superseded
superseded_by: ADR-repository-owned-sdd-execution
created_at: 2026-11-13
supersedes: [ADR-repository-locked-runtime]
---

# [ADR-repository-path-sources] Install repository path sources from the evaluated checkout

Superseded in part by `ADR-repository-owned-sdd-execution`: all decisions assigning path-source capture, identity and installation to Hub.

- **Status**: Superseded by `ADR-repository-owned-sdd-execution`
- **Date**: 2026-11-13
- **Involved Components/Capabilities**: `capabilities/sdd/`

---

## 1. Context & Problem Statement

Repositories develop their own devkit bundles in the repository, or copy them with devkit's bundle snapshot, and
lock them in the devkit dependency group as editable path sources (devkit CAP-DIST-in-repo-bundles). Hub installs
the SDD runtime from the evaluated commit's lock (`ADR-repository-locked-runtime`) and refuses every path or
editable requirement, so such a repository cannot be evaluated at all. A path source is not identified by the lock:
uv records only its location, so a runtime identity derived from the export alone would reuse a runtime built from
earlier bundle content. The install runs in a background task after the disposable checkout may be gone.

## 2. Decision Drivers

- A repository that locks its own bundles is evaluable without operator provisioning.
- A changed bundle in a later commit is evaluated with that commit's content.
- No path source reads outside the evaluated checkout, and build code keeps no network and no credentials.
- Repositories without path sources keep their runtime identity and cache entries.

## 3. Considered Options

1. Keep refusing path sources: no new code, but every repository with an in-repository bundle stays unevaluable.
2. Install path sources editable from the checkout: no copy, but the runtime would depend on a checkout that is
   removed after the request and could change under it.
3. Capture each in-checkout path source tree at selection in the Hub process, hash it into the identity and build
   the captured copy offline in the sandbox like a Git source: evaluable and content-addressed, at the cost of
   reading each tree on every selection.

## 4. Decision Outcome

Chosen option: 3, because it is the only option that makes these repositories evaluable while keeping the runtime
content-addressed and the build sandboxed.

- Path and editable sources of the selected group that resolve inside the evaluated checkout are installed; paths outside it, symlinks on the path or inside the tree, archives and URL sources are refused. → `CAP-SDD-runtime-isolation` rule 4 (MUST)
- The Hub process captures each path source tree at selection, bounded in file count and size, and writes the captured copy into the install's build directory; no fetch or credential is involved. → `CAP-SDD-runtime-isolation` rule 32 (MUST)
- Path sources are built offline in the sandbox with the image's pinned backend and installed as wheels, exactly like Git sources. → `CAP-SDD-runtime-isolation` rule 9 (MUST)
- The runtime identity also covers a deterministic content digest of each path source tree, and is unchanged for a selection without path sources. → `CAP-SDD-runtime-isolation` rule 2 (MUST)
- Supersedes in part `ADR-repository-locked-runtime`: the clause that the runtime identity is the digest of the uv export of that group plus the interpreter minor version.

## 5. Consequences

- Positive: in-repository and snapshot bundles need no publication or Git host to be evaluated; a bundle change
  yields a new runtime.
- Negative: every selection reads and hashes the path source trees in the Hub process, and an install holds their
  content in memory; both are bounded by the capture limits.
- Risk: a pull request can change its own in-repository bundle and thereby the rules that judge it; this is the
  same accepted risk as a lock change under `ADR-repository-locked-runtime`.
- Follow-up: revisit the symlink refusal when a consumer bundle needs a symlink inside its own tree.

## 6. Confirmation

`modules/hub/tests/unit/features/project_management/sdd/test_lock_runtime.py` (selection, refusals, identity),
`modules/hub/tests/unit/features/project_management/sdd/test_runtime_install.py` (Hub-process staging) and the
sandboxed path install in `modules/hub/tests/integration/features/project_management/sdd/test_lock_runtime.py`;
review of the restating `CAP-SDD-runtime-isolation` rules 2, 4, 9 and 32.
