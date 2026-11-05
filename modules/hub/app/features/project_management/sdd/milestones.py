"""Bounded, read-only milestone readiness using a single immutable checkout."""

import asyncio
from urllib.parse import quote

import yaml
from app.features.project_management.branches import activity_branch
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.github import WorkGitHub
from app_layer_base.utils.time_util import get_current_utc_time

from .activities import admission_reason, marker
from .checkout import checkout
from .milestone_graph import LIMITS, MilestoneGraph, metadata, safe_path
from .policy import admission_blocker
from .progress import held
from .runtime import configured_version, restore
from .services import cli, read_hold


def observation_time() -> str:
    return get_current_utc_time().isoformat()


async def _basis(github, repository: str, ref: str) -> str:
    row = await github.optional(f"/repos/{repository}/commits/{quote(ref, safe='')}")
    if row is None:
        raise ProjectError(422, "Requested repository ref does not exist")
    return row["sha"]


async def list_milestones(observer, project, ref: str) -> dict:
    token = await observer.get_token(project.github_connector_id, "github")
    async with asyncio.timeout(LIMITS["deadline_seconds"]), pipeline_services.create_github_client(token) as client:
        sha = await _basis(WorkGitHub(client), project.github_repository, ref)
        async with checkout(project.github_repository, sha, sha, token) as root:
            await restore(root)
            graph = MilestoneGraph(root)
            await graph.load()
            return {
                "resolved_sha": sha,
                "complete": not graph.reasons,
                "reasons": graph.reasons,
                "items": [r for r in graph.documents if r.get("kind") == "milestone"],
            }


async def preview_milestone(observer, project, request, runs_for) -> dict:
    if request.milestone_path:
        safe_path(request.milestone_path)
    token = await observer.get_token(project.github_connector_id, "github")
    result = {
        "project_id": str(project.id),
        "repository": project.github_repository,
        "requested_ref": request.ref,
        "resolved_sha": "",
        "milestone": {"id": request.milestone_id, "path": request.milestone_path},
        "observed_at": observation_time(),
        "runtime_identity": None,
        "complete": False,
        "counts": {"members": 0, "anchors": 0, "edges": 0},
        "limits": LIMITS,
        "reasons": [],
        "warnings": [],
        "nodes": [],
        "edges": [],
        "members": [],
    }
    graph = None
    try:
        async with asyncio.timeout(LIMITS["deadline_seconds"]), pipeline_services.create_github_client(token) as client:
            github = WorkGitHub(client)
            sha = await _basis(github, project.github_repository, request.ref)
            result["resolved_sha"] = sha
            async with checkout(project.github_repository, sha, sha, token) as root:
                result["warnings"] = await restore(root)
                result["runtime_identity"] = configured_version()
                graph = MilestoneGraph(root)
                await graph.load()
                milestone = await graph.milestone(request.milestone_id, request.milestone_path)
                result["milestone"] = milestone
                members = await graph.members(milestone)
                result["counts"]["members"] = len(members)
                if len(members) > LIMITS["members"]:
                    graph.reasons.append("Direct member limit exceeded")
                milestone_holds = await graph.dependencies(milestone)
                for row in members[: LIMITS["members"]]:
                    member = {
                        **row,
                        "activity_kind": None,
                        "stage": None,
                        "admission": "unknown",
                        "scheduling": "held",
                        "workflow_hold": {},
                        "eligibility": "unknown",
                        "reasons": [],
                        "evidence": [],
                        "evidence_observed_at": None,
                    }
                    result["members"].append(member)
                    try:
                        meta = metadata(root, row["path"])
                        status = meta.get("status")
                        activity = "plan" if status == "draft" else "dev" if status == "accepted" else None
                        member["activity_kind"] = activity
                        dependencies = [*milestone_holds, *await graph.dependencies(row)]
                        if milestone.get("status") in ("done", "dropped"):
                            dependencies.append("Milestone is done or dropped; inspection only")
                        member["scheduling"] = "held" if dependencies else "pass"
                        member["reasons"].extend(dependencies)
                        if activity is None:
                            member["eligibility"] = (
                                "finished" if status in ("completed", "handed_off") else "unsupported"
                            )
                            continue
                        slug = row["id"].removeprefix("PROP-")
                        unit = row["path"].removesuffix("/proposal.md")
                        branch = activity_branch(activity, slug)
                        # Native starts only support the global proposal bundle convention.
                        if unit != f"docs/proposals/PROP-{slug}":
                            member["eligibility"] = "unsupported"
                            member["reasons"].append("Native activity start does not support this proposal anchor")
                            continue
                        anchor = (root / row["path"]).read_text(encoding="utf-8")
                        reason = admission_reason(anchor, activity, slug)
                        if reason is None:
                            reason = await admission_blocker(root, unit, activity)
                        member["admission"] = "held" if reason else "pass"
                        if reason:
                            member["reasons"].append(reason)
                        current = await cli(root, "workflow", "next", "--unit", unit)
                        hold = read_hold(current)
                        member["stage"] = (current.get("stage") or {}).get("id")
                        member["workflow_hold"] = hold
                        if current.get("errors"):
                            raise ValueError("Workflow evaluation has invalid evidence")
                        workflow_held = held({"hold": hold}) or bool(hold["malformed_workers"])
                        if workflow_held:
                            member["reasons"].append("Workflow worker evidence holds this unit")
                        existing = await github.optional(
                            f"/repos/{project.github_repository}/git/ref/heads/{quote(branch, safe='')}"
                        )
                        if existing:
                            pulls = await github.reader._get_list(
                                f"/repos/{project.github_repository}/pulls",
                                {
                                    "head": f"{project.github_repository.split('/')[0]}:{branch}",
                                    "state": "open",
                                    "per_page": 100,
                                },
                            )
                            owned = [
                                p
                                for p in pulls
                                if (p.get("head") or {}).get("ref") == branch
                                and marker(activity, slug) in (p.get("body") or "")
                            ]
                            member["evidence_observed_at"] = observation_time()
                            runs = await runs_for(unit)
                            member["evidence"] = [
                                {
                                    "run_id": str(r.id),
                                    "pull_number": r.pull_number,
                                    "head_sha": (r.sdd_progress or {}).get("head_sha"),
                                    "base_sha": (r.sdd_progress or {}).get("base_sha"),
                                }
                                for r in runs
                                if any(p["number"] == r.pull_number for p in owned)
                            ]
                            member["eligibility"] = "existing_activity" if owned else "held"
                            member["reasons"].append(
                                "Existing owned activity; inspection only" if owned else "SDD_BRANCH_EXISTS"
                            )
                        else:
                            member["eligibility"] = (
                                "held" if reason or dependencies or workflow_held else "eligible_now"
                            )
                    except (ProjectError, OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
                        member["eligibility"] = "unknown"
                        member["reasons"].append(
                            f"Evaluation unavailable for {row['id']} ({row['path']}): "
                            + (f"{exc.code}: {exc.detail}" if isinstance(exc, ProjectError) else type(exc).__name__)
                        )
                        graph.reasons.append(f"Partial member evaluation: {row['id']} ({row['path']})")
    except TimeoutError:
        result["reasons"].append("Preview deadline exceeded")
    except ProjectError as exc:
        if exc.detail in (
            "Requested repository ref does not exist",
            "Milestone ID is missing, ambiguous or does not match its exact path",
        ):
            raise
        result["reasons"].append(f"Runtime or repository evaluation unavailable: {exc.code}")
    if graph:
        result["nodes"], result["edges"] = list(graph.nodes.values()), graph.edges
        result["counts"].update(anchors=len(graph.nodes), edges=len(graph.edges))
        result["reasons"].extend(graph.reasons)
        for name in ("anchors", "edges"):
            if result["counts"][name] > LIMITS[name]:
                result["reasons"].append(f"{name} limit exceeded")
    result["complete"] = not result["reasons"]
    if not result["complete"]:
        for member in result["members"]:
            if member["eligibility"] == "eligible_now":
                member["eligibility"] = "unknown"
                member["reasons"].append("Preview incomplete; selection disabled")
    return result
