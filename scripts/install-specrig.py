#!/usr/bin/env python3
"""Provision the pinned release and its official offline restoration cache."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


def install(destination: Path, pin_path: Path) -> None:
    pin = json.loads(pin_path.read_text())
    architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine())
    target = f"{platform.system().lower()}_{architecture}"
    expected_hash = pin["sha256"][target]
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    asset = f"specrig_{pin['version']}_{target}.tar.gz"
    identity = f"specrig version {pin['version']} commit={pin['commit']}"
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        subprocess.run(
            [
                "gh",
                "release",
                "download",
                f"v{pin['version']}",
                "--repo",
                pin["repository"],
                "--pattern",
                asset,
                "--dir",
                str(root),
            ],
            check=True,
        )
        archive = root / asset
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError("specrig archive does not match the reviewed release checksum")
        allowed = {"specrig", "LICENSE", "INSTALL.md", "THIRD_PARTY_NOTICES.txt"}
        with tarfile.open(archive) as package:
            members = package.getmembers()
            if (
                len(members) != len(allowed)
                or {m.name for m in members} != allowed
                or not all(m.isfile() for m in members)
            ):
                raise RuntimeError("unexpected release archive contents")
            for member in members:
                stream = package.extractfile(member)
                assert stream is not None
                (root / member.name).write_bytes(stream.read())
        binary = root / "specrig"
        binary.chmod(0o755)
        actual = subprocess.check_output([str(binary), "--version"], text=True).strip()
        if actual != identity:
            raise RuntimeError("specrig executable does not match the pinned version and commit")
        # Let specrig own the verified-cache format and package validation.
        subprocess.run(
            [
                str(binary),
                "installation",
                "install",
                str(root / "seed"),
                "--version",
                pin["version"],
                "--repository",
                pin["repository"],
                "--cache-dir",
                str(destination / "releases"),
                "--skip-agents",
                "--json",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        cache = destination / "releases" / pin["repository"].replace("/", "_") / f"{pin['version']}_{target}"
        if hashlib.sha256((cache / asset).read_bytes()).hexdigest() != expected_hash:
            raise RuntimeError("offline cache does not match the reviewed release checksum")
        (destination / "bin").mkdir(exist_ok=True)
        # Replace atomically so re-provisioning cannot truncate an in-flight executable.
        with tempfile.NamedTemporaryFile(dir=destination / "bin", delete=False) as staged:
            staged_path = Path(staged.name)
        try:
            shutil.copy2(binary, staged_path)
            staged_path.replace(destination / "bin/specrig")
        finally:
            staged_path.unlink(missing_ok=True)
        for name in allowed - {"specrig"}:
            shutil.copy2(root / name, destination / name)
    (destination / "pin.json").write_text(json.dumps({**pin, "identity": identity}, indent=2) + "\n")
    print(f"Installed {identity} at {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--pin", type=Path, default=Path(__file__).resolve().parent.parent / "config/specrig-release.json"
    )
    args = parser.parse_args()
    install(args.destination, args.pin)
