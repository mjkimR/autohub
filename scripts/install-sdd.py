#!/usr/bin/env python3
"""Provision a separate, locked devkit-spec environment. Never install from a PR's manifest."""

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
    help="Operator-reviewed directory containing pyproject.toml and uv.lock",
)
options = parser.parse_args()
source = options.manifest.resolve()
PACKAGES = ["devkit-core", "devkit-cli", "devkit-dist", "devkit-agt", "devkit-advisory", "devkit-spec"]


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
        raise SystemExit("Runtime changed: provision a fresh destination, then switch AUTOHUB_SDD_HOME")
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
        "import json,sys; from importlib.metadata import version, entry_points; "
        "print(json.dumps({'packages': {n: version(n) for n in sys.argv[1:]}, 'python_prefix': sys.base_prefix, 'bundles': sorted(ep.name for ep in entry_points(group='devkit.bundles'))}))",
        *PACKAGES,
    ],
    text=True,
)
pin = json.loads(versions)
# Hub compares these revisions with a repository's own uv.lock to warn when agents may run another devkit-spec.
pin.update(provider="devkit-spec", lock_sha256=lock_digest, revisions=lock_revisions(source / "uv.lock"))
(destination / "pin.json").write_text(json.dumps(pin, indent=2) + "\n")
print(f"SDD runtime installed: {destination}")
