"""Offline integration seam for lock-derived SDD runtimes.

Fixture repositories commit the seed manifest (``config/sdd-runtime``) as their own ``pyproject.toml`` and
``uv.lock``. The real selection computes that lock's identity, and the cache entry for it is seeded from the venv
``just install-sdd`` provisioned (``AUTOHUB_TEST_SDD_SEED``), so evaluation runs the production lookup, lease and
isolated devkit without network access.
"""

import json
import os
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from app.features.project_management.sdd import runtime, runtime_cache
from app.features.project_management.sdd.lock_runtime import select

MANIFEST = Path(__file__).resolve().parents[4] / "config/sdd-runtime"


def seed_home() -> Path:
    seed = os.environ.get("AUTOHUB_TEST_SDD_SEED")
    if not seed:
        if os.environ.get("AUTOHUB_REQUIRE_SDD"):
            pytest.fail("required devkit-spec seed runtime was not provisioned")
        pytest.skip("requires just test-sdd")
    return Path(seed).resolve()


def devkit_binary() -> str:
    return str(seed_home() / ".venv/bin/devkit")


def write_manifest(root: Path) -> None:
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(MANIFEST / name, root / name)


def seed_identity() -> str:
    """Seed the cache entry for the manifest's identity once per cache; safe across xdist workers."""
    home = seed_home()
    with TemporaryDirectory() as directory:
        write_manifest(Path(directory))
        selection = select(Path(directory))
    if runtime_cache.complete(selection.identity):
        return selection.identity
    deadline = time.monotonic() + 120
    while (claim := runtime_cache.try_build_lock(selection.identity)) is None:
        if runtime_cache.complete(selection.identity) or time.monotonic() > deadline:
            return selection.identity
        time.sleep(0.2)
    try:
        if not runtime_cache.complete(selection.identity):
            staged = runtime_cache.staging(selection.identity)
            shutil.copytree(home / ".venv", staged / ".venv", symlinks=True)
            source = json.loads((home / "pin.json").read_text())
            pin = {
                "provider": "devkit-spec",
                "identity": selection.identity,
                "lock_sha256": selection.identity,
                "group": selection.group,
                "python": selection.python,
                "python_prefix": source["python_prefix"],
                "packages": source.get("packages", {}),
                "bundles": source.get("bundles", []),
                "revisions": {item.package: item.revision for item in selection.git},
            }
            (staged / "pin.json").write_text(json.dumps(pin, indent=2, sort_keys=True))
            runtime_cache.publish(selection.identity, staged)
    finally:
        claim.release()
    return selection.identity


def use_fixture_runtime(root: Path, monkeypatch) -> str:
    """Seed the runtime and let direct evaluations of ``root`` (outside a checkout scope) resolve it."""
    identity = seed_identity()
    fallback = runtime.RuntimeSource(Path(root).resolve(), None)
    original = runtime._source.get

    def current_source():
        return original() or fallback

    monkeypatch.setattr(runtime, "current_source", current_source)
    return identity
