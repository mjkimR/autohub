#!/usr/bin/env python3
"""Check reviewed devkit pins and the vendored viewer offline, without installing anything."""

import base64
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from devkit.advisory import Actor, AdvisoryError, ExitCode, Retry

REPOSITORY = "https://github.com/mjkimR/devkit"
SUBDIRECTORIES = {
    "devkit-agt": "packages/devkit",
    **{
        f"devkit-{name}": f"packages/devkit-{name}"
        for name in ("advisory", "catalog", "cli", "core", "dist", "docs", "spec")
    },
}
DEVELOPMENT_PACKAGES = set(SUBDIRECTORIES)
RUNTIME_PACKAGES = DEVELOPMENT_PACKAGES - {"devkit-catalog"}
PROFILES = (".", "config/sdd-runtime")  # the seed runtime; serving hosts install from repository locks
VIEWER = "devkit-viewer-0.1.0.tgz"


class DevkitPinsError(AdvisoryError):
    code = "DEVKIT_PINS_INVALID"
    actor = Actor.DEVELOPER
    retry = Retry.AFTER_FIX
    input_error = True
    exit_code = ExitCode.FINDINGS


def require(condition: bool, message: str, path: Path) -> None:
    if not condition:
        raise DevkitPinsError(message, target_files=[str(path)])


def check(root: Path) -> tuple[str, str]:
    """All sources, overrides and resolved packages share one immutable commit and release version."""
    manifests = {profile: tomllib.loads((root / profile / "pyproject.toml").read_text()) for profile in PROFILES}
    revision = manifests["."]["tool"]["uv"]["sources"]["devkit-dist"]["rev"]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "Pin devkit to a full Git commit", root / "pyproject.toml")
    versions = set()
    for profile, manifest in manifests.items():
        path = root / profile / "pyproject.toml"
        uv = manifest["tool"]["uv"]
        for name, source in uv["sources"].items():
            if name.startswith("devkit-"):
                require(
                    name in SUBDIRECTORIES
                    and source.get("git", "").removesuffix(".git") == REPOSITORY
                    and source.get("rev") == revision
                    and source.get("subdirectory") == SUBDIRECTORIES[name],
                    f"Align {name} source with the reviewed devkit commit",
                    path,
                )
        for override in uv.get("override-dependencies", []):
            if override.startswith("devkit-"):
                name, separator, url = override.partition(" @ git+")
                parsed = urlsplit(url)
                repo, _, rev = parsed.path.rpartition("@")
                require(
                    bool(separator)
                    and name in SUBDIRECTORIES
                    and f"{parsed.scheme}://{parsed.netloc}{repo}".removesuffix(".git") == REPOSITORY
                    and rev == revision
                    and parse_qs(parsed.fragment).get("subdirectory") == [SUBDIRECTORIES[name]],
                    f"Align {name} override with the reviewed devkit commit",
                    path,
                )
        path = root / profile / "uv.lock"
        packages = {p["name"]: p for p in tomllib.loads(path.read_text())["package"] if p["name"].startswith("devkit-")}
        expected = DEVELOPMENT_PACKAGES if profile == "." else RUNTIME_PACKAGES
        require(set(packages) == expected, "Review the devkit package inventory", path)
        for name, package in packages.items():
            parsed = urlsplit(package["source"].get("git", ""))
            query = parse_qs(parsed.query)
            require(
                f"{parsed.scheme}://{parsed.netloc}{parsed.path}".removesuffix(".git") == REPOSITORY
                and parsed.fragment == revision
                and query.get("rev") == [revision]
                and query.get("subdirectory") == [SUBDIRECTORIES[name]],
                f"Align the resolved {name} Git source with the reviewed devkit commit",
                path,
            )
            versions.add(package["version"])
    require(len(versions) == 1, "Use one devkit release version in all three locks", root / "uv.lock")
    version = versions.pop()
    check_viewer(root, revision, version)
    return revision, version


def check_viewer(root: Path, revision: str, version: str) -> None:
    ui = root / "modules/hub-ui"
    path = ui / "vendor/devkit-viewer.source.json"
    source = json.loads(path.read_text())
    require(
        source["schema"] == 1
        and source["repository"] == REPOSITORY
        and source["commit"] == revision
        and source["version"] == version
        and source["artifact"] == VIEWER,
        "Rebuild the viewer from the reviewed devkit commit and update its source receipt",
        path,
    )
    artifact = (ui / "vendor" / VIEWER).read_bytes()
    require(
        hashlib.sha256(artifact).hexdigest() == source["sha256"],
        "Viewer artifact differs from its source receipt",
        path,
    )
    path = ui / "package-lock.json"
    package = json.loads(path.read_text())["packages"]["node_modules/devkit-viewer"]
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(artifact).digest()).decode()
    require(
        package["resolved"] == f"file:vendor/{VIEWER}" and package["integrity"] == integrity,
        "Reinstall the viewer tarball to refresh npm integrity",
        path,
    )


def main() -> int:
    try:
        revision, version = check(Path(__file__).resolve().parents[1])
    except (DevkitPinsError, OSError, ValueError, KeyError, TypeError) as exc:
        error = exc if isinstance(exc, DevkitPinsError) else DevkitPinsError(str(exc))
        print(error.render(), file=sys.stderr)
        return int(error.exit_code)
    print(f"[DEVKIT_PINS: ok version={version} commit={revision} profiles=3 viewer=verified]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
