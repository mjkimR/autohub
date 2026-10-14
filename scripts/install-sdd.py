#!/usr/bin/env python3
"""Provision a separate, locked devkit-spec environment. Never install from a PR's manifest."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "config/sdd-runtime"
destination = Path(sys.argv[1]).resolve()
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
        "import json,sys; from importlib.metadata import version; "
        "print(json.dumps({'packages': {n: version(n) for n in ['devkit-agt','devkit-advisory','devkit-spec']}, 'python_prefix': sys.base_prefix}))",
    ],
    text=True,
)
pin = json.loads(versions)
pin.update(provider="devkit-spec", lock_sha256=lock_digest)
(destination / "pin.json").write_text(json.dumps(pin, indent=2) + "\n")
print(f"SDD runtime installed: {destination}")
