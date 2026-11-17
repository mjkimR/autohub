#!/usr/bin/env python3
"""Check reviewed Python devkit pins offline, without installing anything."""

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


class DevkitPinsError(AdvisoryError):
    code = "DEVKIT_PINS_INVALID"
    actor = Actor.DEVELOPER
    retry = Retry.AFTER_FIX
    input_error = True
    exit_code = ExitCode.FINDINGS


def require(condition: bool, message: str, path: Path) -> None:
    if not condition:
        raise DevkitPinsError(message, target_files=[str(path)])


def release_parts(version: str, path: Path) -> tuple[int, ...]:
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), f"Use a devkit release version, not {version}", path)
    return tuple(int(part) for part in version.split("."))


def check(root: Path) -> tuple[str, str]:
    """All sources, overrides and resolved packages share one immutable commit and one release series.

    devkit releases selective package versions (ADR-selective-package-versions): only changed
    distributions take the release number, and the devkit-agt meta package always carries it.
    """
    manifest = tomllib.loads((root / "pyproject.toml").read_text())
    revision = manifest["tool"]["uv"]["sources"]["devkit-dist"]["rev"]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", revision)), "Pin devkit to a full Git commit", root / "pyproject.toml")
    path = root / "pyproject.toml"
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
    path = root / "uv.lock"
    packages = {p["name"]: p for p in tomllib.loads(path.read_text())["package"] if p["name"].startswith("devkit-")}
    require(set(packages) == DEVELOPMENT_PACKAGES, "Review the devkit package inventory", path)
    versions: dict[str, tuple[int, ...]] = {}
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
        versions[name] = release_parts(package["version"], path)
    release = versions["devkit-agt"]
    require(
        all(parts[:2] == release[:2] and parts <= release for parts in versions.values()),
        "Resolve every devkit package within the devkit-agt release series",
        path,
    )
    return revision, ".".join(map(str, release))


def main() -> int:
    try:
        revision, version = check(Path(__file__).resolve().parents[1])
    except (DevkitPinsError, OSError, ValueError, KeyError, TypeError) as exc:
        error = exc if isinstance(exc, DevkitPinsError) else DevkitPinsError(str(exc))
        print(error.render(), file=sys.stderr)
        return int(error.exit_code)
    print(f"[DEVKIT_PINS: ok version={version} commit={revision} toolchain=root]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
