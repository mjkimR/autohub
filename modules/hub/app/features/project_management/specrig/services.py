"""CLI-owned stage and policy evaluation, independent of durable transitions."""

import asyncio
import json
import os
from pathlib import Path

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError

from .checkout import checkout, command


def configured_version() -> str:
    version = os.environ.get("AUTOHUB_SPECRIG_VERSION", "").strip()
    if not version:
        raise ProjectError(422, "Set AUTOHUB_SPECRIG_VERSION to the installed specrig --version output")
    return version


async def cli(root: Path, *args: str):
    try:
        return json.loads(await command("specrig", *args, "--format", "json", cwd=root))
    except (ValueError, TypeError):
        raise ProjectError(422, "Unsupported specrig JSON output") from None


class SpecrigService:
    async def inspect(self, repository, spec_dir, pull, token, *, snapshot=None, approved=False):
        head, base = pull["head"]["sha"], pull["base"]["sha"]
        try:
            async with asyncio.timeout(65):
                async with checkout(repository, head, base, token) as root:
                    return await self.evaluate(root, spec_dir, head, base, snapshot, approved)
        except (OSError, TimeoutError):
            raise ProjectError(
                422, "Specrig runner unavailable or timed out; provision Git and the pinned CLI"
            ) from None

    async def evaluate(self, root, spec_dir, head, base, snapshot, approved):
        expected = snapshot["cli_version"] if snapshot else configured_version()
        version = (await command("specrig", "--version", cwd=root)).strip()
        if version != expected:
            raise ProjectError(422, "Specrig CLI version differs from the execution pin")
        if not (root / ".specrig").is_dir() or not (root / spec_dir / "spec.md").is_file():
            raise ProjectError(422, "Initialize specrig and bind an existing spec before execution")
        policy = await cli(root, "config", "show")
        workflow = await cli(root, "workflow", "show", "--spec", spec_dir)
        checks = await cli(root, "workflow", "checks")
        if policy.get("schema_version") != 1 or not isinstance(checks, list):
            raise ProjectError(422, "Unsupported specrig policy or check schema")
        keys = {key: value["value"] for key, value in policy["keys"].items()}
        contract = {
            "mode": "specrig",
            "spec_dir": spec_dir,
            "cli_version": version,
            "workflow_id": workflow["id"],
            "workflow_hash": workflow["hash"],
            "policy": keys,
        }
        if snapshot and any(snapshot.get(key) != value for key, value in contract.items()):
            raise ProjectError(409, "Specrig workflow or policy changed; inspect and enroll a new execution")
        given = ["--given", "approval-given"] if approved else []
        current = await cli(root, "workflow", "next", "--spec", spec_dir, *given)
        if not current.get("bound") or current.get("drift") or current.get("envelope_errors"):
            raise ProjectError(422, "Specrig binding drift or invalid envelope; repair the repository evidence")
        integrated = False
        stage = current.get("stage") or {}
        if approved and "lint-ci-clean" in stage.get("exit", []):
            ancestry = await command("git", "merge-base", head, base, cwd=root)
            if ancestry.strip() == base:
                try:
                    await command("specrig", "lint", "--ci", "--base", base, cwd=root)
                except ProjectError:
                    pass
                else:
                    integrated = True
                    current = await cli(
                        root, "workflow", "next", "--spec", spec_dir, *given, "--given", "lint-ci-clean"
                    )
        evidence = request_digest({"head": head, "base": base, "contract": contract, "current": current})
        return {
            "snapshot": contract,
            "head_sha": head,
            "base_sha": base,
            "workflow": workflow,
            "current": current,
            "evidence_digest": evidence,
            "integrated": integrated,
        }
