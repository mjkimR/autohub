---
id: PLAN-repo-locked-sdd-runtime
spec: SPEC-repo-locked-sdd-runtime
---

# Technical Plan: `SPEC-repo-locked-sdd-runtime` Install the SDD evaluation runtime from the repository lock

## 1. Constitution & Invariant Review

- `CAP-SDD-runtime-isolation` changes: its Scope Excluded ("installation of target dependencies during requests"),
  rules 1-4 (pin, server mapping, evaluation-local profile, bundle inventory), 9 (runtime part of pinned execution),
  10 (revision parity) and 15 (probe) are replaced. `ADR-repository-locked-runtime` and
  `ADR-offline-source-build` authorize these changes; the capability is rewritten at `living-spec-draft`.
- Rule 11 (no network, no inherited credentials, OS isolation) and rule 12 (no unsandboxed fallback) stay and now
  also govern the build step.
- `CAP-SDK-existing-pr-bridge` profile selection and `ARCH-07-deployment` (image packages profiles) change with the
  same ADRs. `ARCH-11-risks-and-technical-debt` "Runtime drift and admitted work" is restated for continuation.
- No other ADR or architecture `MUST` conflicts.

## 2. Architecture Overview & Impact

Runtime selection moves from a server mapping chosen before checkout to a lazy resolution from the checked-out
commit's lock, on the first devkit command in a checkout scope.

| Component | Change |
| --- | --- |
| `sdd/lock_runtime.py` (new) | Parse root `pyproject.toml`/`uv.lock`, choose the group, run `uv export`, classify requirements, compute identity, check `requires-python` |
| `sdd/runtime_cache.py` (new) | Cache root, per-identity cross-process locks, leases, failure markers, eviction |
| `sdd/runtime_install.py` (new) | Hub-process source fetch and wheel install, sandboxed offline builds, `pin.json`, atomic publish |
| `sdd/runtime.py` | Context of the resolved runtime; `ensure_runtime()`; `check_bundles` against the entry's pin; `revision_warnings` removed |
| `sdd/profiles.py` | Removed; `runtime_scope` callers switch to `runtime_source` |
| `sdd/isolation.py` | `git-safe` independent of a devkit venv; `isolated_build_command`; host probe command |
| `sdd/checkout.py` | Checkout scope installs the resolver; `command("devkit")` awaits `ensure_runtime()` |
| `sdd/services.py` | No refusal on a changed CLI identity; `runtime_status` split into host probe and project lock state |
| `sdd/usecases.py`, `sdd/api.py` | Runtime status resolves the project's default-branch head |
| `sdd/batch_evidence.py`, `batch_driver.py` | `runtime` becomes the identity record; `uv.lock` hash dropped from `configuration` |
| `sdd/diagnostics.py` | New codes; `RUNTIME_REVISION_MISMATCH` kept in the catalog only |
| `execution/flows/bridge.py` | Runtime from the operator checkout's lock with the project's connector token |
| `docker/hub.Dockerfile`, `config/sdd-build/` (new) | Pinned hatchling build environment `/opt/sdd-build`, `uv` binary in the runtime stage; profiles removed |
| `config/sdd-runtime/`, `scripts/install-sdd.py`, `scripts/test-sdd.sh` | Kept as the test/dev seed runtime and build-environment installer; app-common profile removed |
| `modules/hub-ui` runtime line | Shows lock state and identity; generated client regenerated |

New dependency: the `uv` binary in the serving image (already used to build it). No new Python package; requirement
parsing uses `packaging`, already locked.

## 3. Component & Interface Design

```text
checkout(repository, head, base, token)
  └─ runtime_source(root, token)            # contextvar: lazy resolver, nothing installed yet
       ├─ command("git-safe", ...)          # sandbox with image Git only, never resolves a runtime
       └─ command("devkit", ...)
            └─ ensure_runtime()
                 ├─ select(root) -> Selection | refusal                 (AC-05/06/07)
                 ├─ complete entry -> lease + home                      (AC-01)
                 ├─ failure marker -> SOURCE_UNAVAILABLE | INSTALL_FAILED (AC-11)
                 └─ start_install (single flight, shielded) -> PREPARING (AC-08/09)
```

```python
# lock_runtime.py
@dataclass(frozen=True)
class Selection:
    group: str | None            # None: main dependencies
    export: str                  # uv export --frozen --offline --no-header --no-annotate --no-emit-project
    identity: str                # sha256(json{"export", "python": "3.13", "build": build_lock_sha256})
    git: tuple[GitSource, ...]   # (repository "owner/name", revision sha, subdirectory, package name)
    registry: tuple[str, ...]    # "name==version ; marker" lines with --hash options

def select(root: Path) -> Selection: ...          # raises ProjectError 422 SDD_RUNTIME_* codes

# runtime_cache.py
def cache_root() -> Path                           # AUTOHUB_SDD_CACHE, default /tmp/autohub-sdd-runtimes
def entry(identity) -> Path                        # <root>/<identity>; complete when pin.json exists
@contextmanager def lease(identity)                # fcntl LOCK_SH on <root>/<identity>.lease; touches mtime
def try_build_lock(identity) -> BuildLock | None   # fcntl LOCK_EX|LOCK_NB on <root>/<identity>.build
def record_failure(identity, code) / failure(identity) -> str | None   # <root>/<identity>.failed, 60 s
def evict(cap_bytes: int) -> list[str]             # LRU by lease mtime; skips entries whose lease is held

# runtime_install.py
async def install(selection: Selection, token: str) -> Path   # staging -> rename to entry(identity)
```

Snapshot `cli_version` is `devkit-lock:<identity>`. `pin.json` keeps `provider: devkit-spec`, `python_prefix`,
`bundles`, package versions and Git `revisions`, and adds `identity` and `group`; no paths or timestamps.

`GET /api/v1/projects/{project_id}/sdd/runtime` response (additive; `profile` constant `repository-lock`):

```json
{"ok": true, "isolation": "bubblewrap", "detail": "Python 3.13.x",
 "profile": "repository-lock", "state": "ready|preparing|failed",
 "identity": "<sha256>|null", "bundles": [], "revisions": {}, "provider": "devkit-spec",
 "lock_sha256": "<identity>|null", "lock_detail": "<catalog text>|null"}
```

Install steps (all in a fresh `mkdtemp` staging directory under the cache root, then `rename` to the entry; the
unique name keeps a process left by an earlier install out of a later one). Only the Hub process
writes the staging root, `pin.json` and the rename; sandboxes write `work/` (builds) or `.venv` (later steps):

1. Hub process: shallow `git fetch` of each distinct (repository, revision) from `https://github.com/` with
   `credential_env(token)` into `work/src/`; check out the revision.
2. Hub process: `uv venv` with the image interpreter, then
   `uv pip install --no-deps --only-binary :all: --require-hashes -r registry.txt` (wheels only: no package code
   runs). This is the last Hub-process use of the venv's interpreter. The Hub creates `.venv/.tmp` (scratch for
   later sandboxes, kept in the entry) and records the identities of `work/` and `.venv`.
3. Sandbox per Git package, writable `work/` only: `uv build --wheel --offline --no-build-isolation --python
   /opt/sdd-build/.venv/bin/python --out-dir work/wheels <source>`; network unshared, environment limited to
   `PATH`, `HOME`, `TMPDIR`, `LANG`, `UV_OFFLINE=1`, `UV_CACHE_DIR`.
4. Hub process: check that `work/` is still the directory it created and that every built wheel is a regular file.
   Sandbox, writable `.venv` only: `uv pip install --offline --no-deps --no-index --no-cache <wheels>`; then check
   `.venv` against its creation-time identity. After the first sandbox step the Hub never acts on a path below
   `.venv`, and removes `work/` only symlink-safely.
5. Sandbox, writable `.venv` only: inventory probe (bundles, versions); check `.venv`. The Hub writes `pin.json`
   (`O_NOFOLLOW`, `O_EXCL`) with its own `python_prefix`, removes `work/` and scratch, renames the staging
   directory to `entry(identity)` and runs `evict` in a thread.

Devkit commands read the interpreter prefix the Hub computes, never the pin's value. An entry whose `.venv` is a
symlink is refused.

## 4. Storage & State Management

- No database migration. Snapshot `cli_version` values change format; stored snapshots keep their old values and
  continue under AC-04 because identity changes no longer refuse.
- Cache state is per instance and disposable: entries, `.lease`, `.build` and `.failed-<scope>` files under the cache
  root. A failure marker is scoped to a hash of the credential that failed. `prune` removes staging whose build
  claim is free and expired markers; staging still in progress counts against the cap.
- `AUTOHUB_SDD_CACHE_BYTES` (default set from AC-18's measurement) bounds entries; the transient uv cache is pruned.
- Batch basis evidence stored before rollout carries the old `runtime` shape; the batch driver compares it as a
  change, which the operator settles before rollout (Section 5).

## 5. Error Handling & Edge Cases

| Condition | Result |
| --- | --- |
| No `uv.lock`, no group or main dependency naming `devkit-spec` | 422 `SDD_RUNTIME_UNLOCKED`, repository, `after_fix` |
| Path/URL/editable requirement, non-GitHub Git, index option | 422 `SDD_RUNTIME_SOURCE_UNSUPPORTED`, repository |
| `requires-python` excludes the image interpreter | 422 `SDD_RUNTIME_PYTHON_UNSUPPORTED`, repository |
| `uv export` fails (lock out of date with pyproject) | 422 `SDD_RUNTIME_UNLOCKED` with the lock remediation |
| Entry incomplete, build lock free or held | 503 `SDD_RUNTIME_PREPARING`, runtime, `safe` |
| Git fetch refused for the connector | failure marker; 422 `SDD_RUNTIME_SOURCE_UNAVAILABLE`, runtime, `after_fix` |
| Wheel missing, hash mismatch, build failure | failure marker; 422 `SDD_RUNTIME_INSTALL_FAILED`, runtime, `after_fix` |
| Receipt bundle absent from the entry's `bundles` | 422 `SDD_BUNDLES_MISSING`, repository |
| No isolation runner | 422 `SDD_ISOLATION_UNAVAILABLE` (unchanged), also for builds |
| Process crash mid-install | staging directory left under `.staging-*`; the next build lock holder removes stale staging |

A failure marker expires after 60 seconds so a corrected setup is retried without operator action. Install runs
as a process-level task shielded from caller cancellation; between requests Cloud Run CPU throttling slows it.
The bridge maps 503 to its existing `bridge-unavailable` retryable result.

Migration and rollback (operations guide): settle active native runs, open batch selections and approved but
unresumed bridge claims before rollout and again before a rollback.

## 6. Verification & Test Plan

| AC | Proof |
| --- | --- |
| AC-03, AC-05, AC-06, AC-07 | `tests/unit/features/project_management/sdd/test_lock_runtime.py` with fixture `pyproject.toml`/`uv.lock` pairs, real `uv export --offline` |
| AC-08, AC-13 | `tests/unit/features/project_management/sdd/test_runtime_cache.py`: two OS processes contend for the build lock; lease blocks eviction |
| AC-09, AC-10, AC-11 | `tests/unit/features/project_management/sdd/test_runtime_install.py` with a fake fetcher and recorded commands; sandboxed build of a local hatchling fixture whose hook tries a socket (integration, `just test-sdd`) |
| AC-01, AC-02, AC-04, AC-12 | `just test-sdd` integration suite with fixture repositories carrying `config/sdd-runtime` locks and a cache seeded from `.cache/sdd`; updated `test_runtime.py`, `test_services.py`, `test_activities.py` |
| AC-14 | `tests/unit/.../test_services.py` runtime status cases; UI `SddExecution.integration.test.ts` |
| AC-15 | `tests/unit/.../test_batch_evidence.py` two cache roots, equal `runtime` |
| AC-16 | `tests/integration/features/execution/flows/test_bridge.py` under `just test-sdd` |
| AC-17 | `tests/unit/.../test_diagnostics.py` historical warning projection |
| AC-18 | Manual cold install of the g-scavenger-crew lock in the image shape; numbers in `materials/cold-install.md` |

Commands: `just test tests/unit/features/project_management/sdd`, `just install-sdd` then `just test-sdd`,
`just test-sdd-pg` for PostgreSQL coverage of the touched integration paths, `just gen-ui-api`, `just test-ui`,
`just lint` and `just check`. The network-dependent cold install (AC-18) is a recorded measurement, not a CI test.
