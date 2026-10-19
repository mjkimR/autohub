"""CLI-owned stage and policy evaluation, independent of durable transitions."""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError

from .checkout import SddCommandError, checkout, command
from .contracts import workflow_hash
from .gates import INTEGRATION_GATE
from .isolation import isolation_runner
from .profiles import current
from .runtime import configured_version, restore, revision_warnings, runtime_pin
from .units import is_proposal, read_status, unit_anchor

STALE_LINT = (
    "Final lint did not run against the committed devkit receipt; run devkit sync with the reviewed runtime, "
    "commit the receipt and enroll the pull request again before integration."
)
STALE_HINT = (
    " This evaluation ran with a stale devkit receipt (RECEIPT_STALE); update the receipt with the reviewed "
    "runtime before repairing anything else."
)


async def cli(root: Path, *args: str):
    try:
        return json.loads(await command("devkit", *args, "--format", "json", cwd=root))
    except (ValueError, TypeError):
        raise ProjectError(422, "Unsupported sdd JSON output") from None


def handoff_target(root: Path, proposal: str) -> str:
    """The spec bundle a proposal was handed off to: ``specs/<YYYY-MM>/<YYYYMMDD>-<slug>``, exactly one."""
    slug = proposal.rsplit("PROP-", 1)[-1]
    found = sorted(
        path.parent.relative_to(root).as_posix()
        for path in (root / "specs").glob(f"*/*-{slug}/spec.md")
        if path.is_file() and not path.is_symlink()
    )
    if len(found) != 1:
        raise ProjectError(
            422,
            f"Handoff of PROP-{slug} not found: expected one specs/<YYYY-MM>/<YYYYMMDD>-{slug}/spec.md, found {len(found)}",
        )
    return found[0]


def committed_configuration(root: Path) -> dict[str, str]:
    """The committed devkit configuration and receipt, read before a sync could rewrite them in the checkout."""
    if not (root / ".devkit/installation.json").is_file():
        raise ProjectError(
            422, "Commit the devkit configuration and installation receipt before enrolling", code="SDD_RECEIPT_MISSING"
        )
    texts = {}
    for name in ("config.toml", "installation.json"):
        path = root / ".devkit" / name
        if path.resolve() != path.absolute() or not path.is_file():
            raise ProjectError(422, "Commit regular devkit configuration and receipt files before enrolling")
        texts[name] = path.read_text()
    return texts


def read_hold(current: dict) -> dict:
    """The hold of the unit's envelopes as ``workflow next`` reports it (section 4 of devkit's envelope contract).

    An unresolved problem or a malformed worker envelope blocks; an unanswered question waits. Bounded for storage
    and display; repository text is shown to operators only through these fields.
    """

    def rows(key: str, fields: tuple[str, ...]) -> list[dict]:
        out = []
        for row in (current.get(key) or [])[:10]:
            if not isinstance(row, dict):
                continue
            entry = {}
            for field in fields:
                value = row.get(field)
                entry[field] = [str(v)[:300] for v in value[:5]] if isinstance(value, list) else str(value or "")[:1000]
            out.append(entry)
        return out

    return {
        "blocked": bool(current.get("blocked")),
        "problems": rows("problems", ("file", "cause", "recovery", "attempts")),
        "pending_questions": rows("pending_questions", ("file", "id", "title")),
        "malformed_workers": rows("malformed_workers", ("file", "reason")),
    }


class SddService:
    async def runtime_status(self) -> dict:
        """Whether this host can evaluate: the runtime pin is consistent and devkit starts inside the sandbox.

        The canary for a new host (Cloud Run needs user namespaces for bubblewrap): no repository is involved.
        """
        try:
            pin = runtime_pin()
        except ProjectError as exc:
            return {"ok": False, "profile": current()[0], "isolation": isolation_runner(), "detail": str(exc)}
        status = {
            "profile": current()[0],
            "bundles": pin.get("bundles", []),
            "provider": pin.get("provider"),
            "lock_sha256": pin.get("lock_sha256"),
            "revisions": {k: str(v) for k, v in (pin.get("revisions") or {}).items()},
            "isolation": isolation_runner(),
        }
        with TemporaryDirectory(prefix="autohub-sdd-probe-") as directory:
            try:
                async with asyncio.timeout(30):
                    version = await command("devkit", "--version", cwd=Path(directory).resolve())
            except ProjectError as exc:
                return {**status, "ok": False, "detail": str(exc)}
            except (OSError, TimeoutError):
                return {**status, "ok": False, "detail": "Isolated devkit did not start within 30 seconds"}
        return {**status, "ok": True, "detail": version.strip()[:200]}

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
        handoff = bool(snapshot and snapshot.get("handoff_pending"))
        if snapshot and "cli_version" not in snapshot:
            snapshot = None  # enrollment of a handoff-first run: no contract to compare yet
        if snapshot and snapshot.get("provider") != "devkit-spec":
            raise ProjectError(409, "Legacy execution is read-only; enroll a new SDD run")
        expected = snapshot["cli_version"] if snapshot else configured_version()
        version = configured_version()
        if version != expected:
            raise ProjectError(422, "SDD CLI version differs from the execution pin")
        if handoff and not (root / spec_dir / "proposal.md").is_file():
            # The handoff moved the proposal into its spec: the run follows that unit from now on (01 section 6.3).
            target = handoff_target(root, spec_dir)
            result = await self.evaluate(root, target, head, base, None, approved)
            result["rebound"] = True
            result["snapshot"]["handoff_from"] = spec_dir
            return result
        anchor = unit_anchor(spec_dir)
        if not (root / ".devkit").is_dir() or anchor is None or not (root / spec_dir / anchor).is_file():
            raise ProjectError(422, "Initialize devkit-spec and bind an existing spec or proposal before execution")
        committed = committed_configuration(root)
        # The repository's lock is parsed in this process (never executed); keep that work off the event loop.
        warnings = [*await restore(root), *await asyncio.to_thread(revision_warnings, root)]
        stale = any(item["code"] == "RECEIPT_STALE" for item in warnings)
        try:
            return await self.evaluate_workflow(
                root, spec_dir, head, base, snapshot, approved, version, committed, warnings
            )
        except SddCommandError as exc:
            if not stale:
                raise
            # A later refusal (workflow drift, invalid evidence) must not hide its likely cause.
            raise SddCommandError(exc.cli_code, exc.detail + STALE_HINT) from exc
        except ProjectError as exc:
            if not stale:
                raise
            raise ProjectError(exc.status, exc.detail + STALE_HINT, code=getattr(exc, "code", None)) from exc

    async def evaluate_workflow(self, root, spec_dir, head, base, snapshot, approved, version, committed, warnings):
        stale = any(item["code"] == "RECEIPT_STALE" for item in warnings)
        policy = await cli(root, "spec", "policy")
        workflow = await cli(root, "workflow", "show", "--unit", spec_dir)
        checks = await cli(root, "workflow", "checks")
        if not isinstance(policy.get("approvals"), dict) or not isinstance(checks.get("checks"), list):
            raise ProjectError(422, "Unsupported sdd policy or check schema")
        keys = policy
        contract = {
            "mode": "sdd",
            "provider": "devkit-spec",
            "contract_version": 1,
            "configuration_digest": request_digest(
                {"config": committed["config.toml"], "receipt": committed["installation.json"]}
            ),
            "spec_dir": spec_dir,
            "cli_version": version,
            "workflow_id": workflow["id"],
            "workflow_hash": workflow_hash(workflow),
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
        given = ["--given", INTEGRATION_GATE] if approved else []
        current = await cli(root, "workflow", "next", "--unit", spec_dir, *given)
        if not current.get("bound") or current.get("drift") or current.get("errors"):
            raise ProjectError(422, "SDD binding drift or invalid envelope; repair the repository evidence")
        hold = read_hold(current)
        held = hold["blocked"] or bool(hold["pending_questions"])
        envelopes = await cli(root, "workflow", "envelope", "check", "--unit", spec_dir)
        reports = []
        for kind in ("final-report", "review", "reverify", "worker"):
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
        lint_blocked = False
        stage = current.get("stage") or {}
        # devkit passes no gate while the unit is held, and its integration guard refuses the merge; so does Hub.
        if approved and not held and "lint-ci-clean" in stage.get("exit", []):
            ancestry = await command("git-safe", "merge-base", head, base, cwd=root)
            if ancestry.strip() == base:
                try:
                    await command("devkit", "rules", "check", "--ci", "--base", base, "--format", "json", cwd=root)
                except SddCommandError as exc:
                    if exc.cli_code == "RULES_VIOLATIONS":
                        lint_diagnostic = exc.detail
                    elif stale and exc.cli_code == "RULES_LOAD_FAILED":
                        # The gate reads the committed tree; a rule its stale receipt records no longer loads.
                        # Agents cannot repair that within this run, so the run pauses instead of dispatching.
                        lint_diagnostic, lint_blocked = STALE_LINT, True
                    else:
                        raise
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
            "lint_blocked": lint_blocked,
            "reports": reports,
            "warnings": warnings,
            "hold": hold,
            "unit_status": read_status(root, spec_dir) if is_proposal(spec_dir) else None,
        }
