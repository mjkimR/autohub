"""Read actual Git and specrig state from an operator-configured checkout."""

import asyncio
import hashlib
import json
import re
from pathlib import Path

from autohub_sdk import content_digest


class BridgeRejected(Exception):
    pass


async def process(*args: str, cwd: Path):
    child = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        async with asyncio.timeout(30):
            stdout, _ = await child.communicate()
    except BaseException:
        if child.returncode is None:
            child.kill()
        await child.wait()
        raise
    if child.returncode != 0:
        raise BridgeRejected("checkout-check-failed")
    return stdout.decode()


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
    show = json.loads(await process("specrig", "workflow", "show", "--spec", spec_dir, "--format", "json", cwd=root))
    current = json.loads(await process("specrig", "workflow", "next", "--spec", spec_dir, "--format", "json", cwd=root))
    stage = current.get("stage") or {}
    if (
        not current.get("bound")
        or current.get("envelope_errors")
        or not stage.get("human_gate")
        or "envelope-final-report-present" not in stage.get("entry", [])
        or "approval-given" not in stage.get("exit", [])
    ):
        raise BridgeRejected("workflow-not-ready-for-integration")
    verified = {
        check
        for item in show.get("stages", [])
        if item["id"] in current.get("done", [])
        for check in item.get("exit", [])
    }
    if not {
        "envelope-review-passed",
        "reconcile-resolved",
        "spec-status-completed",
        "envelope-final-report-present",
    }.issubset(verified):
        raise BridgeRejected("workflow-evidence-checks-missing")
    if show.get("id") != current.get("workflow"):
        raise BridgeRejected("workflow-binding-invalid")
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
