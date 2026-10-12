"""Pinned, offline harness restoration in the disposable evaluation checkout."""

import json
import os
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError

from .checkout import command


def runtime_home() -> Path:
    return Path(os.environ.get("AUTOHUB_SPECRIG_HOME", "/opt/specrig")).resolve()


def configured_version() -> str:
    version = os.environ.get("AUTOHUB_SPECRIG_VERSION", "").strip()
    if version:
        return version
    try:
        pin = json.loads((runtime_home() / "pin.json").read_text())
        return f"specrig version {pin['version']} commit={pin['commit']}"
    except (OSError, ValueError, KeyError, TypeError):
        raise ProjectError(422, "Provision the pinned specrig runtime with just install-specrig") from None


async def restore(root: Path, identity: str) -> None:
    manifest = root / ".specrig/installation.json"
    if not manifest.exists():
        return  # Legacy repositories keep the complete harness in Git.
    try:
        receipt = json.loads(manifest.read_text())
        source = receipt.get("source") or {}
        layered = receipt.get("layout") == "layered"
        if not layered and source.get("kind") != "release":
            return
        recorded = f"specrig version {receipt['version']} commit={receipt['commit']}"
        repository = os.environ.get("AUTOHUB_SPECRIG_REPOSITORY", "mjkimR/specrig")
        if source.get("kind") != "release" or source.get("repository") != repository or recorded != identity:
            raise ValueError("unsupported installation receipt")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ProjectError(
            422,
            "Specrig installation receipt must match the server's pinned release and repository; "
            "upgrade the project or provision its recorded release before enrolling",
            code="SPECRIG_INSTALLATION_MISMATCH",
        ) from None
    await command(
        "specrig",
        "installation",
        "restore",
        str(root),
        "--offline",
        "--cache-dir",
        str(runtime_home() / "releases"),
        "--repository",
        repository,
        "--json",
        cwd=root,
    )
