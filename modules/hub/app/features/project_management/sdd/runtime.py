"""An operator-provisioned Python environment, independent of repository dependencies."""

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

# Packages whose Git revision the runtime pin records and a repository's own lock may pin differently.
PINNED_PACKAGES = ("devkit-spec", "devkit-agt")
LOCK_LIMIT = 8 * 1024 * 1024
RECEIPT_STALE_DETAIL = (
    "The committed devkit receipt, configuration or seeded files are out of date for the reviewed runtime{revision}; "
    "Hub regenerated the managed assets for this evaluation. Run devkit sync with a matching devkit-spec and commit "
    "the result before integration (a receipt change needs a new enrollment)."
)


def runtime_home() -> Path:
    return Path(os.environ.get("AUTOHUB_SDD_HOME", "/opt/sdd")).resolve()


def runtime_pin() -> dict:
    home = runtime_home()
    try:
        pin = json.loads((home / "pin.json").read_text())
        if (
            pin["provider"] != "devkit-spec"
            or pin["lock_sha256"] != hashlib.sha256((home / "uv.lock").read_bytes()).hexdigest()
        ):
            raise ValueError("runtime lock mismatch")
        return pin
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError(
            422, "Provision the locked runtime with just install-sdd", code="SDD_RUNTIME_UNAVAILABLE"
        ) from None


def configured_version() -> str:
    return "devkit-spec:" + runtime_pin()["lock_sha256"]


async def restore(root: Path) -> list[dict]:
    """Restore the Git-ignored managed assets of a checkout from the reviewed runtime; report a stale receipt.

    ``devkit sync --locked`` restores exactly what the committed receipt records. When that receipt no longer
    matches the runtime's packages (``RECEIPT_STALE``), the assets are regenerated with a plain ``devkit sync``
    instead and the mismatch is returned as a warning: the checkout is disposable, so the repository's commits
    stay untouched, and the packages are the operator's, so nothing unreviewed runs. Every other failure blocks.
    """
    from .checkout import SddCommandError, command

    if not (root / ".devkit/installation.json").is_file():
        raise ProjectError(
            422, "Commit the devkit configuration and installation receipt before enrolling", code="SDD_RECEIPT_MISSING"
        )
    try:
        await command("devkit", "sync", "--locked", "--format", "json", cwd=root)
    except SddCommandError as exc:
        if exc.cli_code != "RECEIPT_STALE":
            raise
        await command("devkit", "sync", "--format", "json", cwd=root)
        return [stale_warning()]
    return []


def stale_warning() -> dict:
    """The RECEIPT_STALE warning, naming the runtime's devkit-spec revision when the pin records one."""
    try:
        revisions = runtime_pin().get("revisions")
    except ProjectError:
        revisions = None
    revision = revisions.get("devkit-spec") if isinstance(revisions, dict) else None
    named = f" (devkit-spec {str(revision)[:12]})" if isinstance(revision, str) and revision else ""
    return {"code": "RECEIPT_STALE", "detail": RECEIPT_STALE_DETAIL.format(revision=named)}


def lock_revisions(text: str) -> dict[str, str]:
    """Exact Git revisions of the pinned packages in a uv.lock; anything else in the file is ignored."""
    try:
        packages = tomllib.loads(text).get("package", [])
    except (tomllib.TOMLDecodeError, RecursionError):  # repository content: malformed or hostile input is no signal
        return {}
    revisions: dict[str, str] = {}
    for package in packages if isinstance(packages, list) else []:
        if not isinstance(package, dict) or package.get("name") not in PINNED_PACKAGES:
            continue
        source = package.get("source")
        git = source.get("git") if isinstance(source, dict) else None
        revision = git.rsplit("#", 1)[-1] if isinstance(git, str) else ""
        if re.fullmatch(r"[0-9a-f]{40}", revision):
            revisions[package["name"]] = revision
    return revisions


def revision_warnings(root: Path) -> list[dict]:
    """Best-effort parity signal: the repository's locked devkit revisions against the runtime pin's.

    Agents work from the repository's own devkit installation, which Hub cannot inspect; a root ``uv.lock``
    is its only committed trace. Only exact revisions are compared, and only revisions are displayed.
    """
    pinned = runtime_pin().get("revisions")
    lock = root / "uv.lock"
    if not isinstance(pinned, dict) or lock.is_symlink() or not lock.is_file() or lock.stat().st_size > LOCK_LIMIT:
        return []
    try:
        locked = lock_revisions(lock.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []
    return [
        {
            "code": "RUNTIME_REVISION_MISMATCH",
            "detail": (
                f"The repository locks {name} at {locked[name][:12]} while the reviewed runtime provides "
                f"{str(pinned[name])[:12]}; agents and Hub may follow different workflow definitions."
            ),
        }
        for name in PINNED_PACKAGES
        if name in locked and isinstance(pinned.get(name), str) and locked[name] != pinned[name]
    ]
