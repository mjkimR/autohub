"""Bounded immutable content evidence used only by execution selection."""

import hashlib
import json

import yaml
from app.features.project_management.pipeline_runs.requests import request_digest

from .milestone_graph import metadata
from .runtime import runtime_pin
from .services import cli


def content_basis(root, row):
    path = row["path"]
    meta = metadata(root, path)
    body = (root / path).read_text(encoding="utf-8").split("---", 2)[2]
    stable = {k: v for k, v in meta.items() if k not in ("status", "depends_on")}
    return {
        "id": row["id"],
        "path": path,
        "status": meta.get("status"),
        "depends_on": meta.get("depends_on", []),
        "content_digest": request_digest(json.loads(json.dumps({"meta": stable, "body": body}, default=str))),
    }


async def capture_basis(root, graph, members):
    config = {}
    for name in (".devkit/config.toml", ".devkit/installation.json", "uv.lock"):
        path = root / name
        config[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {
        "members": [content_basis(root, row) for row in members],
        "configuration": config,
        "runtime": runtime_pin(),
        "policy": await cli(root, "spec", "policy"),
    }


async def completed_spec(observer, project, ref, target, merge_sha):
    from app.features.project_management.pipelines import services as pipeline_services
    from app.features.project_management.work_plans.github import WorkGitHub

    from .checkout import checkout, command
    from .milestone_graph import MilestoneGraph, safe_path
    from .milestones import _basis
    from .runtime import restore

    safe_path(target + "/spec.md")
    token = await observer.get_token(project.github_connector_id, "github")
    async with pipeline_services.create_github_client(token) as client:
        sha = await _basis(WorkGitHub(client), project.github_repository, ref)
    async with checkout(project.github_repository, sha, sha, token) as root:
        await restore(root)
        await command("git-safe", "merge-base", "--is-ancestor", merge_sha, sha, cwd=root)
        meta = metadata(root, target + "/spec.md")
        identity = meta.get("id")
        if not isinstance(identity, str) or not identity.startswith("SPEC-") or meta.get("status") != "completed":
            return None
        graph = MilestoneGraph(root)
        await graph.load()
        resolved = await graph.resolve(identity)
        if graph.reasons or not resolved or resolved.get("path") != target + "/spec.md":
            return None
        return {"id": identity, "path": target + "/spec.md", "observed_sha": sha}


async def confirmed_ancestry(observer, project, before, after):
    if before == after:
        return True
    from urllib.parse import quote

    from app.features.project_management.pipelines import services as pipeline_services
    from app.features.project_management.work_plans.github import WorkGitHub

    token = await observer.get_token(project.github_connector_id, "github")
    async with pipeline_services.create_github_client(token) as client:
        comparison = await WorkGitHub(client).optional(
            f"/repos/{project.github_repository}/compare/{quote(before, safe='')}...{quote(after, safe='')}"
        )
    return bool(
        comparison
        and comparison.get("status") in ("ahead", "identical")
        and (comparison.get("merge_base_commit") or {}).get("sha") == before
    )


async def accepted_proposal(observer, project, ref, path, merge_sha):
    """Capture the one allowed Planning transformation at its exact confirmed merge."""
    from app.features.project_management.pipelines import services as pipeline_services
    from app.features.project_management.work_plans.github import WorkGitHub

    from .checkout import checkout
    from .milestones import _basis

    token = await observer.get_token(project.github_connector_id, "github")
    async with pipeline_services.create_github_client(token) as client:
        selected_sha = await _basis(WorkGitHub(client), project.github_repository, ref)
    if not await confirmed_ancestry(observer, project, merge_sha, selected_sha):
        return None
    async with checkout(project.github_repository, merge_sha, merge_sha, token) as root:
        basis = content_basis(root, {"id": metadata(root, path).get("id"), "path": path})
        return basis if basis["status"] == "accepted" else None


async def remote_head(observer, project, ref):
    from app.features.project_management.pipelines import services as pipeline_services
    from app.features.project_management.work_plans.github import WorkGitHub

    from .milestones import _basis

    token = await observer.get_token(project.github_connector_id, "github")
    async with pipeline_services.create_github_client(token) as client:
        return await _basis(WorkGitHub(client), project.github_repository, ref)


async def canonical_resolutions(root, identities):
    from app.features.project_management.projects.errors import ProjectError

    from .milestone_graph import LIMITS, is_anchor

    if len(set(identities)) > LIMITS["anchors"]:
        raise ProjectError(422, "Retained canonical resolution budget exceeded")
    result = {}
    for identity in sorted(set(identities)):
        try:
            response = await cli(root, "docs", "resolve", identity)
            rows = response.get("documents", [])
            if response.get("errors") or len(rows) != 1:
                continue
            row = rows[0]
            if row.get("kind") == "spec" and row.get("status") == "completed" and is_anchor(row):
                meta = metadata(root, row["path"])
                if meta.get("id") == row["id"] and meta.get("status") == "completed":
                    result[identity] = {"id": row["id"], "path": row["path"], "kind": "spec", "status": "completed"}
        except (ProjectError, OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
            # Missing legacy anchors remain a hold unless a separate exact published repair is proven.
            continue
    return result
