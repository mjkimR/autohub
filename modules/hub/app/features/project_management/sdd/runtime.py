"""An operator-provisioned Python environment, independent of repository dependencies."""

import hashlib
import json
import os
from pathlib import Path

from app.features.project_management.projects.errors import ProjectError


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


async def restore(root: Path, identity: str) -> None:
    from .checkout import command

    if not (root / ".devkit/installation.json").is_file():
        raise ProjectError(
            422, "Commit the devkit configuration and installation receipt before enrolling", code="SDD_RECEIPT_MISSING"
        )
    await command("devkit", "sync", "--locked", "--format", "json", cwd=root)
