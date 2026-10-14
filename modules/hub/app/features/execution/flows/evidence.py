"""Read actual Git and sdd state from an operator-configured checkout."""

import asyncio
import hashlib
import re
from pathlib import Path

from autohub_sdk import content_digest


class BridgeRejected(Exception):
    pass


async def process(*args: str, cwd: Path):
    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.sdd.checkout import command

    try:
        return await command("git-safe", *args[1:], cwd=cwd)
    except ProjectError as exc:
        raise BridgeRejected("checkout-check-failed") from exc


async def read_evidence(checkout: str, spec_dir: str, head_sha: str) -> str:
    # Leaves time for the PR owner's 30-second GitHub read inside the 60-second lease.
    async with asyncio.timeout(25):
        return await _read_evidence(checkout, spec_dir, head_sha)


async def _read_evidence(checkout: str, spec_dir: str, head_sha: str) -> str:
    root = Path(checkout).resolve(strict=True)
    if not re.fullmatch(r"specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+", spec_dir):
        raise BridgeRejected("spec-path-invalid")
    spec = (root / spec_dir).resolve(strict=True)
    if not spec.is_relative_to(root) or not spec.is_dir():
        raise BridgeRejected("spec-path-invalid")
    if (await process("git", "rev-parse", "HEAD", cwd=root)).strip() != head_sha:
        raise BridgeRejected("checkout-head-changed")
    if (await process("git", "status", "--porcelain", "--untracked-files=normal", cwd=root)).strip():
        raise BridgeRejected("checkout-dirty")
    from app.features.project_management.projects.errors import ProjectError
    from app.features.project_management.sdd.progress import approval_gate
    from app.features.project_management.sdd.services import SddService

    try:
        evidence = await SddService().evaluate(root, spec_dir, head_sha, head_sha, None, False)
    except ProjectError as exc:
        raise BridgeRejected("workflow-evaluation-failed") from exc
    if not approval_gate(evidence):
        raise BridgeRejected("workflow-not-ready-for-integration")
    show = evidence["workflow"]
    files = {}
    for path in sorted(spec.rglob("*")):
        if path.is_file():
            if not path.resolve().is_relative_to(spec):
                raise BridgeRejected("evidence-path-invalid")
            files[str(path.relative_to(spec))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if (await process("git", "rev-parse", "HEAD", cwd=root)).strip() != head_sha:
        raise BridgeRejected("checkout-head-changed")
    if (await process("git", "status", "--porcelain", "--untracked-files=normal", cwd=root)).strip():
        raise BridgeRejected("checkout-dirty")
    return content_digest({"head_sha": head_sha, "workflow_hash": show["hash"], "files": files})
