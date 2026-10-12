#!/usr/bin/env python3
"""Build a test-only release/cache from the pinned upcoming layered CLI source."""

import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
from pathlib import Path

source, output = (Path(p).resolve() for p in sys.argv[1:])
pin = json.loads((Path(__file__).resolve().parent.parent / "config/specrig-release.json").read_text())
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
if commit != pin["compatibility_commit"]:
    raise SystemExit("Compatibility source must match the reviewed commit")
version = "0.0.0"  # Test fixture, never a published/release candidate identity.
architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
system = platform.system().lower()
suffix = f"{system}_{architecture}"
cache = output / "releases" / pin["repository"].replace("/", "_") / f"{version}_{suffix}"
cache.mkdir(parents=True, exist_ok=True)
subprocess.run(
    ["just", "build"],
    cwd=source,
    env={**os.environ, "SPECRIG_VERSION": version, "SPECRIG_OUTPUT": str(cache / "specrig")},
    check=True,
)
for name in ("LICENSE", "INSTALL.md", "THIRD_PARTY_NOTICES.txt"):
    (cache / name).write_text("Local compatibility fixture; not for distribution.\n")
names = ("specrig", "LICENSE", "INSTALL.md", "THIRD_PARTY_NOTICES.txt")
archive = cache / f"specrig_{version}_{suffix}.tar.gz"
with tarfile.open(archive, "w:gz") as stream:
    for name in names:
        stream.add(cache / name, arcname=name)


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


(cache / "verified.json").write_text(
    json.dumps(
        {
            "version": version,
            "commit": commit,
            "repository": pin["repository"],
            "platform": f"{system}/{architecture}",
            "archive_hash": digest(archive),
            "files": {name: digest(cache / name) for name in names},
        }
    )
)
(output / "bin").mkdir(exist_ok=True)
binary = output / "bin/specrig"
if binary.is_symlink():
    binary.unlink()
binary.symlink_to(cache / "specrig")
(output / "pin.json").write_text(json.dumps({"version": version, "commit": commit, "repository": pin["repository"]}))
print(f"Prepared test-only layered runtime at {output}")
