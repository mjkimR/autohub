---
id: PLAN-repo-path-runtime-sources
spec: SPEC-repo-path-runtime-sources
---

# Technical Plan: `SPEC-repo-path-runtime-sources` Install repository-local path sources in the SDD runtime

## 1. Constitution & Invariant Review

- `CAP-SDD-runtime-isolation` rule 4 (path and editable requirements refused) and rule 2 with the identity document
  in its section 4 change. `ADR-repository-locked-runtime` states the identity as the digest of the uv export plus
  the interpreter minor version, so the new `ADR-repository-path-sources` supersedes that clause in part and
  authorizes the rule changes. The capability's Scope Excluded and install steps are restated at
  `living-spec-draft`.
- `ADR-offline-source-build` stays in force unchanged: path sources need no fetch and no credential, and their
  builds use the same offline sandbox step (rule 9). Rules 8, 9, 11, 22, 23 and 25 keep governing every step.
- `ARCH-11-risks-and-technical-debt` records the trust in the evaluated lock; a path source is repository content
  of that same commit, so no new risk entry is needed.

## 2. Architecture Overview & Impact

| Component | Change |
| --- | --- |
| `sdd/lock_runtime.py` | Classify `-e ./<path>` and `./<path>` export lines; name each from the lock; capture each tree from the checkout (no symlinks, bounded); add the tree digests to the identity |
| `sdd/runtime_install.py` | Write each captured path source under `work/src/path-<n>` in the Hub process before any sandbox; build it with the Git sources |
| `sdd/runtime.py`, `sdd/diagnostics.py` | Catalog text names in-repository path sources as supported (wording only) |

No new dependency. `services.py`, `checkout.py`, the bridge and the UI keep calling `select()` and see only a new
identity value.

## 3. Component & Interface Design

```text
select(root)
  ├─ render(manifest, lock, group)          # unchanged: temp dir, uv export --frozen --offline
  ├─ classify(export) -> git, registry, locals   # locals: normalized relative paths ("tools/my-bundle")
  ├─ path_sources(root, locals, lock)       # Hub process, checkout read only
  │    ├─ name from lock: source.editable | source.directory == path
  │    ├─ walk components from root: each a real directory, never a symlink
  │    ├─ regular pyproject.toml
  │    └─ capture files (O_NOFOLLOW, sorted), skip .git/.venv/__pycache__, budget 10,000 files / 32 MiB
  └─ identity(export, {path: digest})      # "paths" key only when non-empty
install(selection, token)
  ├─ fetch_sources(...)                     # Git only, unchanged
  ├─ stage_paths(selection, staged)         # Hub process writes captured bytes to work/src/path-<n>
  ├─ install_wheels(...)                    # unchanged
  └─ build_sources(git + path packages)     # unchanged sandbox build + sandboxed wheel install
```

```python
@dataclass(frozen=True)
class PathSource:
    package: str          # canonical name from the lock
    path: str             # normalized POSIX path relative to the checkout root
    digest: str           # tree digest
    files: tuple[tuple[str, bool, bytes], ...]  # (relative POSIX path, executable, content), sorted; not in repr

@dataclass(frozen=True)
class Selection:
    ...                   # unchanged fields
    paths: tuple[PathSource, ...] = ()

def classify(export: str) -> tuple[tuple[GitSource, ...], tuple[str, ...], tuple[str, ...]]: ...
def tree_digest(files) -> str  # sha256(json [[path, "x" | "-", sha256(content)], ...]) in sorted path order
def identity(export: str, paths: dict[str, str] | None = None) -> str
```

Identity document: `{"build", "export", "python"}` as before, plus `"paths": {<path>: <tree digest>}` only when the
selection has path sources. Existing identities stay unchanged (AC-02).

Choices inside the agreed intent:

- The tree hash goes into `identity()` (called by `select()`): `select()` already owns the checkout read, and
  `identity()` stays the single definition both selection and tests use.
- The content is captured at selection, not re-read at install: the install runs in a background task after the
  checkout scope may have ended and the disposable checkout was removed (AC-06). Capturing also makes the built
  content exactly the hashed content.
- Symlinks are refused rather than followed or skipped: a refusal cannot escape the checkout and never silently
  builds something other than the commit's content.
- `devkit-spec` may itself be a path source, so devkit's own repository and snapshots of it are evaluable.

## 4. Storage & State Management

No database or cache layout change. A new identity value appears for locks with path sources; entries for other
locks keep their identity. The captured content lives in the `Selection` only; it is released when selection's
caller and the install task finish.

## 5. Error Handling & Edge Cases

| Condition | Result |
| --- | --- |
| Path line `../x`, `/abs`, `.`, a component outside `[A-Za-z0-9._-]`, hashes or a marker | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` at classification |
| No lock package names the path | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` |
| Component missing, not a directory or a symlink; `pyproject.toml` missing or a symlink | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` |
| Symlink, FIFO, socket or device inside the tree, or a file that changes type while read | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` |
| More than 10,000 files or 32 MiB across the selection's path sources | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED` with the limits in its text |
| Path source build fails (other backend, broken package) | failure marker, 422 `SDD_RUNTIME_INSTALL_FAILED` (unchanged) |

## 6. Verification & Test Plan

| AC | Proof |
| --- | --- |
| AC-01, AC-02, AC-03, AC-04 | `tests/unit/features/project_management/sdd/test_lock_runtime.py` with the new `fixtures/path-lock` (real offline `uv export`) |
| AC-05, AC-06 | `tests/unit/features/project_management/sdd/test_runtime_install.py` with the fake runner; `tests/integration/features/project_management/sdd/test_lock_runtime.py` real offline sandboxed install of `fixtures/path-only-lock` under `just test-sdd` |

Commands: `just test tests/unit/features/project_management/sdd`, `just test`, `just test-sdd <seed>` with the pinned
build environment, `just lint`, `just check` and `uv run devkit rules check --ci --base 32c69e5`. The fixture locks
are generated once with `uv lock --offline` and committed.
