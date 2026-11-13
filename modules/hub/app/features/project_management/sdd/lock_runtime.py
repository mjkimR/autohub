"""Select the devkit runtime a commit's own uv.lock pins, without executing repository code.

The Hub process parses the root manifest and lock and lets uv render the locked requirements of the dependency
group that declares devkit-spec (or the main dependencies). uv reads TOML only (``--frozen --offline``); nothing is
built or downloaded here. The rendered text, the interpreter and the build environment define the identity.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from app.features.project_management.projects.errors import ProjectError
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name

MANIFEST_LIMIT = 1024 * 1024
LOCK_LIMIT = 8 * 1024 * 1024
EXPORT_TIMEOUT = 20
_GIT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*) @ git\+https://github\.com/"
    r"(?P<owner>[A-Za-z0-9][A-Za-z0-9-]*)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?"
    r"@(?P<rev>[0-9a-f]{40})(?:#subdirectory=(?P<subdirectory>[A-Za-z0-9_./-]+))?$"
)
_REGISTRY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9.+!_-]+(?: ; .+)?$")
_HASH = re.compile(r"^--hash=sha256:[0-9a-f]{64}$")

UNLOCKED = (
    "Commit a root uv.lock whose project declares devkit-spec in a dependency group or its dependencies; "
    "Hub installs the SDD runtime only from that lock."
)
UNSUPPORTED = (
    "Lock devkit and its bundle packages only from PyPI wheels or https://github.com Git sources; path, URL, "
    "editable and custom index sources are not installed by Hub."
)


@dataclass(frozen=True)
class GitSource:
    package: str
    repository: str  # owner/name on github.com
    revision: str
    subdirectory: str


@dataclass(frozen=True)
class Selection:
    group: str | None  # None selects the project's main dependencies
    export: str
    identity: str
    python: str
    git: tuple[GitSource, ...]
    registry: tuple[str, ...]  # requirement lines including their --hash options


def interpreter() -> Path:
    """The interpreter every runtime is created with: the image's own, never a downloaded one."""
    return Path(os.environ.get("AUTOHUB_SDD_PYTHON") or sys.executable)


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def build_home() -> Path:
    return Path(os.environ.get("AUTOHUB_SDD_BUILD", "/opt/sdd-build")).resolve()


def build_digest() -> str:
    lock = build_home() / "uv.lock"
    return hashlib.sha256(lock.read_bytes()).hexdigest() if lock.is_file() else "none"


def uv_binary() -> str:
    return os.environ.get("AUTOHUB_UV") or shutil.which("uv") or "uv"


def _refuse(code: str, detail: str) -> ProjectError:
    return ProjectError(422, detail, code=code)


def _read(path: Path, limit: int) -> str | None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _names(entries) -> set[str]:
    names = set()
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, str):
            try:
                names.add(canonicalize_name(Requirement(entry).name))
            except InvalidRequirement:
                continue
    return names


def choose_group(project: dict) -> str | None:
    """The first dependency group naming devkit-spec, or None when the main dependencies name it."""
    groups = project.get("dependency-groups")
    for name, entries in groups.items() if isinstance(groups, dict) else []:
        if isinstance(name, str) and "devkit-spec" in _names(entries):
            return name
    if "devkit-spec" in _names((project.get("project") or {}).get("dependencies")):
        return None
    raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED)


def check_python(project: dict) -> None:
    spec = (project.get("project") or {}).get("requires-python")
    if spec is None:
        return
    try:
        allowed = SpecifierSet(str(spec))
    except InvalidSpecifier:
        raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED) from None
    full = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if not allowed.contains(full, prereleases=True):
        raise _refuse(
            "SDD_RUNTIME_PYTHON_UNSUPPORTED",
            f"The repository's requires-python excludes Python {python_version()}, the only interpreter Hub "
            "provides for SDD runtimes; widen requires-python to include it.",
        )


def render(manifest: str, lock: str, group: str | None) -> str:
    """uv's own rendering of the locked requirements; it reads only the two copied files."""
    with TemporaryDirectory(prefix="autohub-sdd-export-") as directory:
        root = Path(directory)
        (root / "pyproject.toml").write_text(manifest, encoding="utf-8")
        (root / "uv.lock").write_text(lock, encoding="utf-8")
        selector = ["--only-group", group] if group is not None else ["--no-dev"]
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": directory,
            "UV_NO_CONFIG": "1",
            "UV_PYTHON_DOWNLOADS": "never",
            "UV_CACHE_DIR": str(root / ".uv-cache"),
            "NO_COLOR": "1",
        }
        args = [uv_binary(), "export", "--directory", directory, "--frozen", "--offline", "--no-header"]
        args += ["--no-annotate", "--no-emit-project", "--format", "requirements-txt", *selector]
        try:
            result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=EXPORT_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            raise ProjectError(
                503, "The uv binary for SDD runtime selection is unavailable", code="SDD_RUNTIME_UNAVAILABLE"
            ) from None
        if result.returncode:
            raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED)
        return result.stdout


def classify(export: str) -> tuple[tuple[GitSource, ...], tuple[str, ...]]:
    """Split rendered requirements into GitHub Git sources and hashed registry wheels; refuse anything else."""
    git: list[GitSource] = []
    registry: list[str] = []
    logical: list[str] = []
    current = ""
    for raw in export.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        current = f"{current} {line[:-1].strip()}".strip() if line.endswith("\\") else f"{current} {line}".strip()
        if not line.endswith("\\"):
            logical.append(current)
            current = ""
    if current:
        logical.append(current)
    for line in logical:
        if line.startswith("-"):
            raise _refuse("SDD_RUNTIME_SOURCE_UNSUPPORTED", UNSUPPORTED)
        parts = line.split(" --hash=")
        requirement, hashes = parts[0].strip(), [f"--hash={value.strip()}" for value in parts[1:]]
        if match := _GIT.match(requirement):
            if hashes:
                raise _refuse("SDD_RUNTIME_SOURCE_UNSUPPORTED", UNSUPPORTED)
            subdirectory = (match["subdirectory"] or "").strip("/")
            if ".." in subdirectory.split("/"):
                raise _refuse("SDD_RUNTIME_SOURCE_UNSUPPORTED", UNSUPPORTED)
            git.append(
                GitSource(
                    package=canonicalize_name(match["name"]),
                    repository=f"{match['owner']}/{match['repo']}",
                    revision=match["rev"],
                    subdirectory=subdirectory,
                )
            )
        elif _REGISTRY.match(requirement) and hashes and all(_HASH.match(value) for value in hashes):
            registry.append(" ".join([requirement, *hashes]))
        else:
            raise _refuse("SDD_RUNTIME_SOURCE_UNSUPPORTED", UNSUPPORTED)
    return tuple(git), tuple(registry)


PYPI = "https://pypi.org/simple"


def check_registries(lock: dict, registry: tuple[str, ...]) -> None:
    """uv export names no index, so the lock tells whether each exported registry package comes from PyPI."""
    sources: dict[str, set[str]] = {}
    for package in lock.get("package", []) if isinstance(lock.get("package"), list) else []:
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            source = package.get("source")
            url = source.get("registry") if isinstance(source, dict) else None
            sources.setdefault(canonicalize_name(package["name"]), set()).add(url if isinstance(url, str) else "")
    for line in registry:
        name = canonicalize_name(line.split("==", 1)[0].split("[", 1)[0])
        if sources.get(name, {""}) - {PYPI}:
            raise _refuse("SDD_RUNTIME_SOURCE_UNSUPPORTED", UNSUPPORTED)


def identity(export: str) -> str:
    document = {"export": export, "python": python_version(), "build": build_digest()}
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()


def select(root: Path) -> Selection:
    """The runtime selection of the checked-out commit at ``root``; refusals name only Hub-authored text."""
    manifest = _read(root / "pyproject.toml", MANIFEST_LIMIT)
    lock = _read(root / "uv.lock", LOCK_LIMIT)
    if manifest is None or lock is None:
        raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED)
    try:
        project = tomllib.loads(manifest)
    except (tomllib.TOMLDecodeError, RecursionError):
        raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED) from None
    group = choose_group(project)
    check_python(project)
    export = render(manifest, lock, group)
    git, registry = classify(export)
    try:
        check_registries(tomllib.loads(lock), registry)
    except (tomllib.TOMLDecodeError, RecursionError):
        raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED) from None
    if not any(source.package == "devkit-spec" for source in git) and not any(
        canonicalize_name(line.split("==", 1)[0].split("[", 1)[0]) == "devkit-spec" for line in registry
    ):
        raise _refuse("SDD_RUNTIME_UNLOCKED", UNLOCKED)
    return Selection(
        group=group,
        export=export,
        identity=identity(export),
        python=python_version(),
        git=git,
        registry=registry,
    )
