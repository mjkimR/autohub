"""Per-instance cache of lock-derived SDD runtimes, safe across worker processes.

An entry ``<root>/<identity>`` is complete once its ``pin.json`` exists; it is published by renaming a finished
staging directory, so readers never see a partial runtime. ``fcntl`` locks coordinate processes: an exclusive
``.build`` lock admits one installer per identity, and shared ``.lease`` locks keep an entry from eviction while an
evaluation uses it. A ``.failed-<scope>`` marker holds the last install failure code for a short retry delay, scoped
to the credential that failed so another project's connector is not refused by it.

Entries are content-addressed and shared by every project on the instance that locks the same runtime; Hub
accepts that sharing because one operator owns every project of an instance.
"""

import fcntl
import hashlib
import json
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path

DEFAULT_CAP_BYTES = 256 * 1024 * 1024  # about eight 29 MiB entries; see the spec materials
FAILURE_SECONDS = 60
STAGING_PREFIX = ".staging-"


def cache_root() -> Path:
    root = Path(os.environ.get("AUTOHUB_SDD_CACHE", "/tmp/autohub-sdd-runtimes")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def cap_bytes() -> int:
    try:
        return max(0, int(os.environ.get("AUTOHUB_SDD_CACHE_BYTES", DEFAULT_CAP_BYTES)))
    except ValueError:
        return DEFAULT_CAP_BYTES


def entry(identity: str) -> Path:
    return cache_root() / identity


def complete(identity: str) -> bool:
    return (entry(identity) / "pin.json").is_file()


def _lock_file(identity: str, suffix: str) -> Path:
    return cache_root() / f"{identity}{suffix}"


class BuildLock:
    """An exclusive per-identity install claim; released on close or process exit."""

    def __init__(self, identity: str, handle):
        self.identity, self._handle = identity, handle

    def release(self) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None


def try_build_lock(identity: str) -> BuildLock | None:
    handle = open(_lock_file(identity, ".build"), "a+")  # noqa: SIM115 - held until release
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return BuildLock(identity, handle)


def staging(identity: str) -> Path:
    """A fresh staging directory; only the build lock holder calls this, after removing stale staging."""
    for stale in cache_root().glob(f"{STAGING_PREFIX}{identity}-*"):
        shutil.rmtree(stale, ignore_errors=True)
    path = cache_root() / f"{STAGING_PREFIX}{identity}-{os.getpid()}"
    path.mkdir()
    return path


def publish(identity: str, staged: Path) -> Path:
    """Atomically make a finished staging directory the entry; an existing complete entry wins."""
    target = entry(identity)
    if complete(identity):
        shutil.rmtree(staged, ignore_errors=True)
        return target
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)  # incomplete leftover from an interrupted publish
    os.rename(staged, target)
    return target


@contextmanager
def lease(identity: str):
    """Hold the entry against eviction for one evaluation; touching the file records recent use.

    Never waits: while an eviction holds the entry, BlockingIOError tells the caller to treat it as preparing.
    """
    path = _lock_file(identity, ".lease")
    with open(path, "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        os.utime(path)
        try:
            yield entry(identity)
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def token_scope(token: str | None) -> str:
    """A non-reversible label of the credential an install used; never the credential itself."""
    return hashlib.sha256((token or "").encode()).hexdigest()[:16]


def record_failure(identity: str, code: str, scope: str = "") -> None:
    _lock_file(identity, f".failed-{scope}").write_text(json.dumps({"code": code, "at": time.time()}))


def clear_failure(identity: str) -> None:
    for marker in cache_root().glob(f"{identity}.failed-*"):
        marker.unlink(missing_ok=True)


def failure(identity: str, scope: str = "") -> str | None:
    """The last install failure code for this credential while its retry delay lasts."""
    path = _lock_file(identity, f".failed-{scope}")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or time.time() - float(data.get("at", 0)) > FAILURE_SECONDS:
        return None
    code = data.get("code")
    return code if isinstance(code, str) else None


def _size(path: Path) -> int:
    total = 0
    for current, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(current, name)).st_size
            except OSError:
                continue
    return total


def prune() -> int:
    """Remove staging left by crashed installs (whose build claim is free) and expired failure markers.

    Returns the bytes of staging still in progress, which count against the cap.
    """
    root, active = cache_root(), 0
    for staged in root.glob(f"{STAGING_PREFIX}*"):
        identity = staged.name[len(STAGING_PREFIX) :].rsplit("-", 1)[0]
        claim = try_build_lock(identity)
        if claim is None:
            active += _size(staged)
            continue
        try:
            shutil.rmtree(staged, ignore_errors=True)
        finally:
            claim.release()
    for marker in root.glob("*.failed-*"):
        try:
            if time.time() - marker.stat().st_mtime > FAILURE_SECONDS:
                marker.unlink(missing_ok=True)
        except OSError:
            continue
    return active


def evict(limit: int | None = None) -> list[str]:
    """Remove least-recently-leased complete entries until the total fits; never one whose lease is held.

    Blocking file work: callers on the event loop run it in a thread.
    """
    limit = cap_bytes() if limit is None else limit
    root = cache_root()
    in_progress = prune()
    entries = [path for path in root.iterdir() if path.is_dir() and (path / "pin.json").is_file()]
    sizes = {path.name: _size(path) for path in entries}
    total = sum(sizes.values()) + in_progress

    def last_used(path: Path) -> float:
        lease_file = root / f"{path.name}.lease"
        return lease_file.stat().st_mtime if lease_file.exists() else path.stat().st_mtime

    removed = []
    for path in sorted(entries, key=last_used):
        if total <= limit:
            break
        with open(root / f"{path.name}.lease", "a+") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue  # in use by an evaluation in some process
            try:
                shutil.rmtree(path, ignore_errors=True)
                total -= sizes[path.name]
                removed.append(path.name)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
    return removed
