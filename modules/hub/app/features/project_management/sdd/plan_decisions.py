"""Proposal acceptance and rejection as commits Hub writes itself, without an agent (strategy layer 01 sections
4.2 and 6.2).

Acceptance records ``gate:plan-accept`` with devkit and sets ``status: accepted``; rejection sets ``status: rejected``
only, with the person's reason in the commit message, and closes every open worker question with an answer envelope
(``choice: null``) so the hold does not keep the Planning branch from merging. devkit writes inside the sandbox, Git
commits there too, and the push happens outside it under a lease on the head the person confirmed.
"""

import asyncio
import json
import os
import re

from app.features.project_management.projects.errors import ProjectError
from app_layer_base.utils.time_util import get_current_utc_time

from .checkout import checkout, command, push_head
from .gates import PLAN_ACCEPT_REQUEST
from .progress import held
from .units import proposal_slug, set_status

PLAN_DECISIONS = ("accept_plan", "reject_plan")
DEFAULT_IDENTITY = "AutoHub <autohub@users.noreply.github.com>"
REJECTION_DECISION = "Planning ended by rejection"


def commit_identity() -> tuple[str, str]:
    """Hub's Git identity for decision commits: ``Name <email>`` from AUTOHUB_SDD_COMMIT_IDENTITY."""
    value = os.environ.get("AUTOHUB_SDD_COMMIT_IDENTITY", DEFAULT_IDENTITY)
    match = re.fullmatch(r"\s*([^<>]+?)\s*<([^<>\s]+@[^<>\s]+)>\s*", value)
    if match is None:
        raise ProjectError(422, "Set AUTOHUB_SDD_COMMIT_IDENTITY as 'Name <email>'", code="SDD_IDENTITY_INVALID")
    return match.group(1), match.group(2)


def commit_message(decision: str, slug: str, actor: str, note: str, head: str) -> tuple[str, str]:
    """The commit title and body; the rejection reason leads so the squash merge keeps it (01 section 6.2)."""
    lines = [line.strip() for line in note.splitlines() if line.strip()]
    trailer = f"Decided-by: {actor}\nHead: {head}"
    if decision == "accept_plan":
        body = "\n\n".join(part for part in (note.strip(), trailer) if part)
        return f"Accept proposal PROP-{slug}", body
    first = lines[0][:120] if lines else "no reason given"
    return f"Reject proposal PROP-{slug}: {first}", f"{note.strip()}\n\n{trailer}"


def closure_answers(pending_questions: list[dict], reason: str) -> dict[str, str]:
    """One answers file per worker envelope: every open question answered outside its options with the reason."""
    first = next((line.strip() for line in reason.splitlines() if line.strip()), "")
    decision = f"{REJECTION_DECISION}: {first}" if first else REJECTION_DECISION
    grouped: dict[str, list[str]] = {}
    for row in pending_questions:
        worker = str(row.get("file", "")).rsplit("/", 1)[-1]
        if re.fullmatch(r"worker-[0-9]+\.yaml", worker) and re.fullmatch(r"[a-z][a-z0-9-]*", str(row.get("id", ""))):
            grouped.setdefault(worker, []).append(str(row["id"]))
    return {
        worker: "".join(f"- question: {q}\n  choice: null\n  decision: {json.dumps(decision)}\n" for q in ids)
        for worker, ids in grouped.items()
    }


async def record_plan_decision(
    service,
    repository: str,
    unit: str,
    pull: dict,
    token: str,
    *,
    decision: str,
    actor: str,
    note: str,
    snapshot: dict,
    expected_digest: str,
    request_id: str,
) -> dict:
    """Write the decision into a disposable checkout of the confirmed head, commit it there and publish it.

    Returns what the run records: the action, the confirmed head, the commit that carries the decision, the
    branch, and the commit message the merge reuses.
    """
    from .services import cli

    head, base, branch = pull["head"]["sha"], pull["base"]["sha"], str(pull["head"]["ref"])
    slug = proposal_slug(unit)
    name, email = commit_identity()
    title, body = commit_message(decision, slug, actor, note, head)
    try:
        async with asyncio.timeout(90):
            async with checkout(repository, head, base, token) as root:
                evidence = await service.evaluate(root, unit, head, base, snapshot, False)
                if evidence["evidence_digest"] != expected_digest:
                    raise ProjectError(409, "Workflow evidence changed while recording the decision")
                if decision == "accept_plan":
                    if held(evidence) or not any(
                        r["id"] == PLAN_ACCEPT_REQUEST for r in evidence["current"].get("requests", [])
                    ):
                        raise ProjectError(409, "Proposal is not waiting for acceptance; inspect the latest result")
                    await cli(
                        root,
                        "workflow",
                        "answer",
                        "--unit",
                        unit,
                        "--request",
                        PLAN_ACCEPT_REQUEST,
                        "--action",
                        "accept",
                        "--by",
                        actor,
                        "--note",
                        f"autohub-decision:{request_id} {note}".strip(),
                    )
                    set_status(root, unit, "reviewing", "accepted")
                else:
                    set_status(root, unit, "reviewing", "rejected")
                    pending = (evidence.get("hold") or {}).get("pending_questions") or []
                    for worker, text in closure_answers(pending, note).items():
                        answers = root / ".devkit/transient/hub-tmp" / f"answers-{worker}"
                        answers.parent.mkdir(parents=True, exist_ok=True)
                        answers.write_text(text, encoding="utf-8")
                        await cli(
                            root,
                            "workflow",
                            "envelope",
                            "answer",
                            "--unit",
                            unit,
                            "--answers-to",
                            worker,
                            "--answers-file",
                            str(answers),
                            "--summary",
                            REJECTION_DECISION,
                        )
                await command("git-safe", "add", "-A", "--", unit, cwd=root)
                await command(
                    "git-safe",
                    "-c",
                    f"user.name={name}",
                    "-c",
                    f"user.email={email}",
                    "commit",
                    "--quiet",
                    "-m",
                    title,
                    "-m",
                    body,
                    cwd=root,
                )
                commit_sha = (await command("git-safe", "rev-parse", "HEAD", cwd=root)).strip()
                await push_head(root, repository, branch, head, token)
    except (OSError, TimeoutError):
        raise ProjectError(422, "SDD runner unavailable or timed out; provision Git and the pinned CLI") from None
    return {
        "action": decision,
        "actor": actor,
        "head_sha": head,
        "commit_sha": commit_sha,
        "branch": branch,
        "note": note,
        "commit_title": title,
        "commit_body": body,
        "decided_at": get_current_utc_time().isoformat(),
    }


def plan_approval(plan: dict) -> dict:
    """The approval the merge path reads for a decided proposal: the decision commit is the authorized head."""
    return {
        "actor": plan["actor"],
        "source": "plan-decision",
        "observed_at": plan["decided_at"],
        "head_sha": plan["commit_sha"],
        "evidence_digest": None,
        "saw_ready": False,
    }
