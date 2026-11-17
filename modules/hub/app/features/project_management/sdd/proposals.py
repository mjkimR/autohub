"""Display repository proposal metadata; activity starts never infer workflow eligibility."""

import asyncio
import re
from urllib.parse import quote

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.repositories.services import INLINE_BLOB_LIMIT, blob_cache
from app.features.project_management.work_plans.github import WorkGitHub

from .activities import _frontmatter_value, _text

PROPOSAL_LIMIT = 50


def _slug(name: str) -> str | None:
    slug = name.removeprefix("PROP-")
    return slug if name.startswith("PROP-") and slug and slug[0].isalnum() and slug == slug.lower() else None


def waiting_run(runs) -> dict | None:
    run = next((r for r in runs if r.state not in FINAL_RUN_STATES), None)
    if run is None:
        return None
    return {
        "id": str(run.id),
        "state": run.state,
        "revision": run.revision,
        "pause_reason": run.pause_reason,
        "pull_number": run.pull_number,
        "head_sha": (run.pull_snapshot or {}).get("head_sha"),
    }


def proposal_state(
    slug: str,
    anchor: str | None,
    branches: set[str],
    pulls: dict[str, int],
    run: dict | None,
    approach: str | None = None,
) -> dict:
    status = (_frontmatter_value(anchor, "status") if anchor else None) or "unknown"
    plan, dev = f"plan-{slug}" in branches, f"dev-{slug}" in branches
    display = status
    actions = [] if run else ["start_planning", "start_development"]
    note = "Repository setup and workflow eligibility are the working agent's responsibility"
    return {
        "slug": slug,
        "id": f"PROP-{slug}",
        "path": f"docs/proposals/PROP-{slug}",
        "title": (_frontmatter_value(anchor, "title") if anchor else None) or f"PROP-{slug}",
        "status": status,
        "display_status": display,
        "task_kind": _frontmatter_value(anchor, "task_kind") if anchor else None,
        **{
            field: value if value in ("low", "medium", "high") else None
            for field in ("planning_effort", "dev_effort")
            for value in [_frontmatter_value(anchor or "", field)]
        },
        "plan_branch": plan,
        "dev_branch": dev,
        "plan_pull": pulls.get(f"plan-{slug}"),
        "dev_pull": pulls.get(f"dev-{slug}"),
        "run": run,
        "actions": actions,
        "note": note,
    }


def _tree_proposals(tree) -> tuple[list[str], int, dict[str, str]] | None:
    """Proposal directory names, the directory's entry count and anchor blob SHAs from a recursive tree."""
    entries = tree.get("tree") if isinstance(tree, dict) and not tree.get("truncated") else None
    if not isinstance(entries, list):
        return None
    names: list[str] = []
    count = 0
    anchors: dict[str, str] = {}
    for entry in entries:
        path = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str):
            continue
        if re.fullmatch(r"docs/proposals/[^/]+", path):
            count += 1
            if entry.get("type") == "tree":
                names.append(path.rsplit("/", 1)[-1])
        elif (match := re.fullmatch(r"docs/proposals/([^/]+)/proposal\.md", path)) and entry.get("type") == "blob":
            anchors[match[1]] = str(entry.get("sha", ""))
    return names, count, anchors


async def _anchor_text(github: WorkGitHub, root: str, repository: str, sha: str) -> str | None:
    """A proposal anchor by blob SHA: immutable content, so the shared repository blob cache can answer it."""
    if not sha:
        return None
    if cached := blob_cache.get(repository, sha):
        _, encoding, content = cached
        return content if encoding == "utf-8" else None
    entry = await github.optional(f"{root}/git/blobs/{sha}")
    text = _text(entry)
    if text is not None and isinstance(entry, dict) and int(entry.get("size") or 0) <= INLINE_BLOB_LIMIT:
        blob_cache.put(repository, sha, int(entry.get("size") or 0), "utf-8", text)
    return text


async def list_proposals(observer, project, base_branch: str, runs_for) -> dict:
    """Read the base's proposals and the remote activity branches; ``runs_for(unit)`` returns the unit's runs."""
    token = await observer.get_token(project.github_connector_id, "github")
    repository = project.github_repository
    root = f"/repos/{repository}"
    async with asyncio.timeout(45), pipeline_services.create_github_client(token) as client:
        github = WorkGitHub(client)
        base = await github.optional(f"{root}/git/ref/heads/{quote(base_branch, safe='')}")
        if base is None:
            raise ProjectError(422, f"Base branch {base_branch} is not on the remote")
        base_sha = base["object"]["sha"]
        # One recursive tree read names every proposal and its anchor SHA; a truncated tree falls back
        # to listing the directory and reading each anchor by path.
        found = _tree_proposals(await github.optional(f"{root}/git/trees/{base_sha}", {"recursive": 1}))
        if found is None:
            listing = await github.optional_list(f"{root}/contents/docs/proposals", {"ref": base_sha}) or []
            names = [str(entry.get("name", "")) for entry in listing if entry.get("type") == "dir"]
            count, anchor_shas = len(listing), None
        else:
            names, count, anchor_shas = found
        slugs = sorted(slug for name in names if (slug := _slug(name)))[:PROPOSAL_LIMIT]
        branches: set[str] = set()
        for prefix in ("plan-", "dev-"):
            refs = await github.optional_list(f"{root}/git/matching-refs/heads/{prefix}") or []
            branches |= {str(r.get("ref", "")).removeprefix("refs/heads/") for r in refs}
        open_pulls = await github.reader._get_list(f"{root}/pulls", {"state": "open", "per_page": 100})
        pulls = {str((p.get("head") or {}).get("ref")): int(p["number"]) for p in open_pulls if p.get("number")}
        if anchor_shas is None:
            entries = await asyncio.gather(
                *(
                    github.optional(f"{root}/contents/docs/proposals/PROP-{slug}/proposal.md", {"ref": base_sha})
                    for slug in slugs
                )
            )
            texts = [_text(entry) for entry in entries]
        else:
            texts = await asyncio.gather(
                *(_anchor_text(github, root, repository, anchor_shas.get(f"PROP-{slug}", "")) for slug in slugs)
            )
    items = []
    for slug, text in zip(slugs, texts, strict=True):
        runs = await runs_for(f"docs/proposals/PROP-{slug}")
        items.append(proposal_state(slug, text, branches, pulls, waiting_run(runs)))
    return {
        "base_branch": base_branch,
        "base_sha": base_sha,
        "items": items,
        "truncated": count > PROPOSAL_LIMIT,
    }
