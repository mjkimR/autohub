"""Cross-process build claims, atomic publication, leases and eviction of lock-derived runtimes."""

import multiprocessing
import os
import time

import pytest
from app.features.project_management.sdd import runtime_cache as cache

IDENTITY = "a" * 64


@pytest.fixture(autouse=True)
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOHUB_SDD_CACHE", str(tmp_path / "cache"))
    return tmp_path / "cache"


def _contend(root, identity, results):
    os.environ["AUTOHUB_SDD_CACHE"] = root
    claim = cache.try_build_lock(identity)
    results.put(claim is not None)
    time.sleep(0.5)
    if claim:
        claim.release()


def test_only_one_process_claims_an_identity(root):
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    workers = [context.Process(target=_contend, args=(str(root), IDENTITY, results)) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(10)
    assert sorted(results.get(timeout=5) for _ in workers) == [False, True]


def test_claim_is_free_again_after_release():
    first = cache.try_build_lock(IDENTITY)
    assert first is not None and cache.try_build_lock(IDENTITY) is None
    first.release()
    second = cache.try_build_lock(IDENTITY)
    assert second is not None
    second.release()


def _stage(identity, size=10):
    staged = cache.staging(identity)
    (staged / "blob").write_bytes(b"x" * size)
    (staged / "pin.json").write_text("{}")
    return staged


def test_publication_is_atomic_and_removes_stale_staging(root):
    stale = root / f"{cache.STAGING_PREFIX}{IDENTITY}-1"
    stale.mkdir(parents=True)
    staged = _stage(IDENTITY)
    assert not stale.exists() and not cache.complete(IDENTITY)
    cache.publish(IDENTITY, staged)
    assert cache.complete(IDENTITY) and not staged.exists()


def test_an_existing_complete_entry_wins_publication():
    cache.publish(IDENTITY, _stage(IDENTITY, 1))
    late = _stage(IDENTITY, 99)
    cache.publish(IDENTITY, late)
    assert (cache.entry(IDENTITY) / "blob").stat().st_size == 1 and not late.exists()


def test_failure_markers_expire(monkeypatch):
    cache.record_failure(IDENTITY, "SDD_RUNTIME_SOURCE_UNAVAILABLE")
    assert cache.failure(IDENTITY) == "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    now = time.time()
    monkeypatch.setattr(cache.time, "time", lambda: now + cache.FAILURE_SECONDS + 1)
    assert cache.failure(IDENTITY) is None


def test_eviction_skips_leased_entries_and_removes_least_recent():
    old, used, new = "b" * 64, "c" * 64, "d" * 64
    for identity in (old, used, new):
        cache.publish(identity, _stage(identity, 1000))
        with cache.lease(identity):
            pass
        time.sleep(0.02)
    with cache.lease(old):  # the oldest is in use by an evaluation
        removed = cache.evict(2100)  # three entries of 1002 bytes
    assert removed == [used] and cache.complete(old) and cache.complete(new)


def test_eviction_stops_when_only_leased_entries_remain():
    cache.publish(IDENTITY, _stage(IDENTITY, 5000))
    with cache.lease(IDENTITY):
        assert cache.evict(0) == []
    assert cache.complete(IDENTITY)


def test_failure_markers_are_scoped_to_the_credential():
    cache.record_failure(IDENTITY, "SDD_RUNTIME_SOURCE_UNAVAILABLE", cache.token_scope("narrow"))
    assert cache.failure(IDENTITY, cache.token_scope("narrow")) == "SDD_RUNTIME_SOURCE_UNAVAILABLE"
    assert cache.failure(IDENTITY, cache.token_scope("broad")) is None
    assert "narrow" not in cache.token_scope("narrow")
    cache.clear_failure(IDENTITY)
    assert cache.failure(IDENTITY, cache.token_scope("narrow")) is None


def test_prune_removes_abandoned_staging_and_counts_active_staging(root):
    abandoned = root / f"{cache.STAGING_PREFIX}{'1' * 64}-99"
    abandoned.mkdir(parents=True)
    active = root / f"{cache.STAGING_PREFIX}{'2' * 64}-98"
    active.mkdir()
    (active / "blob").write_bytes(b"x" * 500)
    claim = cache.try_build_lock("2" * 64)
    assert claim is not None
    try:
        assert cache.prune() == 500
    finally:
        claim.release()
    assert not abandoned.exists() and active.exists()


def test_lease_never_waits_for_an_eviction(root):
    import fcntl

    cache.publish(IDENTITY, _stage(IDENTITY))
    with open(root / f"{IDENTITY}.lease", "a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)  # an eviction in progress
        with pytest.raises(BlockingIOError), cache.lease(IDENTITY):
            pass
