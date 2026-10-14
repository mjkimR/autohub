"""CLI-owned stage and policy evaluation, independent of durable transitions."""

import asyncio
import json
from pathlib import Path

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError

from .checkout import SddCommandError, checkout, command
from .runtime import configured_version, restore


async def cli(root: Path, *args: str):
    try:
        return json.loads(await command("devkit", *args, "--format", "json", cwd=root))
    except (ValueError, TypeError):
        raise ProjectError(422, "Unsupported sdd JSON output") from None


class SddService:
    async def inspect(self, repository, spec_dir, pull, token, *, snapshot=None, approved=False, operation=None):
        head, base = pull["head"]["sha"], pull["base"]["sha"]
        try:
            async with asyncio.timeout(65):
                async with checkout(repository, head, base, token) as root:
                    result = await self.evaluate(root, spec_dir, head, base, snapshot, approved)
                    if operation:
                        if result["evidence_digest"] != operation["expected_digest"]:
                            raise ProjectError(409, "Workflow evidence changed while preparing the decision")
                        from .decisions import prepare_record

                        result["prepared_record"] = await prepare_record(root, spec_dir, operation, cli)
                    return result
        except (OSError, TimeoutError):
            raise ProjectError(422, "SDD runner unavailable or timed out; provision Git and the pinned CLI") from None

    async def evaluate(self, root, spec_dir, head, base, snapshot, approved):
        if snapshot and snapshot.get("provider") != "devkit-spec":
            raise ProjectError(409, "Legacy execution is read-only; enroll a new SDD run")
        expected = snapshot["cli_version"] if snapshot else configured_version()
        version = configured_version()
        if version != expected:
            raise ProjectError(422, "SDD CLI version differs from the execution pin")
        if not (root / ".devkit").is_dir() or not (root / spec_dir / "spec.md").is_file():
            raise ProjectError(422, "Initialize devkit-spec and bind an existing spec before execution")
        await restore(root, version)
        policy = await cli(root, "spec", "policy")
        workflow = await cli(root, "workflow", "show", "--unit", spec_dir)
        checks = await cli(root, "workflow", "checks")
        if not isinstance(policy.get("approvals"), dict) or not isinstance(checks.get("checks"), list):
            raise ProjectError(422, "Unsupported sdd policy or check schema")
        for name in ("config.toml", "installation.json"):
            path = root / ".devkit" / name
            if path.resolve() != path.absolute() or not path.is_file():
                raise ProjectError(422, "Commit regular devkit configuration and receipt files before enrolling")
        keys = policy
        contract = {
            "mode": "sdd",
            "provider": "devkit-spec",
            "contract_version": 1,
            "configuration_digest": request_digest(
                {
                    "config": (root / ".devkit/config.toml").read_text(),
                    "receipt": (root / ".devkit/installation.json").read_text(),
                }
            ),
            "spec_dir": spec_dir,
            "cli_version": version,
            "workflow_id": workflow["id"],
            "workflow_hash": workflow["hash"],
            "policy": keys,
        }
        pinned = dict(snapshot or contract)
        if snapshot and any(
            w.get("workflow_id") == contract["workflow_id"] and w.get("workflow_hash") == contract["workflow_hash"]
            for w in snapshot.get("authorized_workflows", [])
        ):
            pinned.update(workflow_id=contract["workflow_id"], workflow_hash=contract["workflow_hash"])
        if snapshot and any(pinned.get(key) != value for key, value in contract.items()):
            raise ProjectError(409, "SDD workflow or policy changed; inspect and enroll a new execution")
        given = ["--given", "integration"] if approved else []
        current = await cli(root, "workflow", "next", "--unit", spec_dir, *given)
        if not current.get("bound") or current.get("drift") or current.get("errors"):
            raise ProjectError(422, "SDD binding drift or invalid envelope; repair the repository evidence")
        envelopes = await cli(root, "workflow", "envelope", "check", "--unit", spec_dir)
        reports = []
        for kind in ("final-report", "review", "reverify"):
            candidates = [row for row in envelopes.get("envelopes", []) if row.get("kind") == kind]
            if candidates:
                latest = max(candidates, key=lambda row: row.get("seq", 0))
                reports.append(
                    {
                        "kind": kind,
                        "file": latest["file"],
                        "status": latest["status"],
                        "summary": str(latest.get("summary", ""))[:4000],
                        "checks": {str(k): str(v)[:1000] for k, v in list((latest.get("checks") or {}).items())[:20]},
                    }
                )
        integrated = False
        lint_diagnostic = None
        stage = current.get("stage") or {}
        if approved and "lint-ci-clean" in stage.get("exit", []):
            ancestry = await command("git-safe", "merge-base", head, base, cwd=root)
            if ancestry.strip() == base:
                try:
                    await command("devkit", "rules", "check", "--ci", "--base", base, "--format", "json", cwd=root)
                except SddCommandError as exc:
                    if exc.cli_code != "RULES_VIOLATIONS":
                        raise
                    lint_diagnostic = exc.detail
                else:
                    integrated = True
                    current = await cli(
                        root, "workflow", "next", "--unit", spec_dir, *given, "--given", "lint-ci-clean"
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
            "lint_diagnostic": lint_diagnostic,
            "reports": reports,
        }
