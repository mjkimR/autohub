#!/usr/bin/env python3
"""Provision a locked environment from an operator-reviewed manifest.

Two manifests use it: ``config/sdd-build`` (the pinned hatchling backend serving images package as
``/opt/sdd-build`` for offline source builds) and ``config/sdd-runtime`` (the devkit seed runtime that integration
tests and local development use). Serving hosts install repository runtimes from each repository's own lock.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
parser.add_argument(
    "--manifest",
    type=Path,
    default=Path(__file__).resolve().parents[1] / "config/sdd-runtime",
    help="Reviewed directory containing pyproject.toml and uv.lock (config/sdd-runtime or config/sdd-build)",
)
options = parser.parse_args()
source = options.manifest.resolve()
PACKAGES = ["devkit-core", "devkit-cli", "devkit-dist", "devkit-agt", "devkit-advisory", "devkit-docs", "devkit-spec"]


def lock_revisions(lock: Path) -> dict[str, str]:
    """The exact Git revision the lock resolves for each devkit package (the fragment of its git source)."""
    revisions = {}
    for package in tomllib.loads(lock.read_text()).get("package", []):
        revision = (package.get("source") or {}).get("git", "").rsplit("#", 1)[-1]
        if package.get("name") in PACKAGES and re.fullmatch(r"[0-9a-f]{40}", revision):
            revisions[package["name"]] = revision
    return revisions


destination = options.destination.resolve()
destination.mkdir(parents=True, exist_ok=True)
lock_digest = hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest()
if (destination / "pin.json").exists():
    previous = json.loads((destination / "pin.json").read_text())
    if previous.get("lock_sha256") != lock_digest:
        raise SystemExit("Manifest changed: provision a fresh destination")
for name in ("pyproject.toml", "uv.lock"):
    shutil.copyfile(source / name, destination / name)
env = {**os.environ, "UV_PROJECT_ENVIRONMENT": str(destination / ".venv")}
# Git sees private repository credentials only during provisioning. No token is stored in URLs or the lock.
if token := env.get("GH_TOKEN"):
    env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader")
    import base64

    env["GIT_CONFIG_VALUE_0"] = "AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
subprocess.run(
    ["uv", "sync", "--project", str(destination), "--locked", "--no-dev", "--no-editable"], env=env, check=True
)
python = destination / ".venv/bin/python"
versions = subprocess.check_output(
    [
        str(python),
        "-I",
        "-c",
        "import json,sys; from importlib.metadata import distributions, entry_points; "
        "installed = {d.metadata['Name'].lower(): d.version for d in distributions()}; "
        "print(json.dumps({'packages': {n: installed[n] for n in sys.argv[1:] if n in installed}, 'python_prefix': sys.base_prefix, 'bundles': sorted(ep.name for ep in entry_points(group='devkit.bundles'))}))",
        *PACKAGES,
    ],
    text=True,
)
pin = json.loads(versions)
pin.update(provider="devkit-spec", lock_sha256=lock_digest, revisions=lock_revisions(source / "uv.lock"))
(destination / "pin.json").write_text(json.dumps(pin, indent=2) + "\n")
print(f"SDD runtime installed: {destination}")
