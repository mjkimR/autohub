"""Display repository proposal metadata; activity starts never infer workflow eligibility."""

import asyncio
from urllib.parse import quote

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
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
        "plan_accept_open": False,
        "decided": False,
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


async def list_proposals(observer, project, base_branch: str, runs_for) -> dict:
    """Read the base's proposals and the remote activity branches; ``runs_for(unit)`` returns the unit's runs."""
    token = await observer.get_token(project.github_connector_id, "github")
    root = f"/repos/{project.github_repository}"
    async with asyncio.timeout(45), pipeline_services.create_github_client(token) as client:
        github = WorkGitHub(client)
        base = await github.optional(f"{root}/git/ref/heads/{quote(base_branch, safe='')}")
        if base is None:
            raise ProjectError(422, f"Base branch {base_branch} is not on the remote")
        base_sha = base["object"]["sha"]
        listing = await github.optional_list(f"{root}/contents/docs/proposals", {"ref": base_sha}) or []
        slugs = sorted(
            slug for entry in listing if entry.get("type") == "dir" and (slug := _slug(str(entry.get("name", ""))))
        )[:PROPOSAL_LIMIT]
        branches: set[str] = set()
        for prefix in ("plan-", "dev-"):
            refs = await github.optional_list(f"{root}/git/matching-refs/heads/{prefix}") or []
            branches |= {str(r.get("ref", "")).removeprefix("refs/heads/") for r in refs}
        open_pulls = await github.reader._get_list(f"{root}/pulls", {"state": "open", "per_page": 100})
        pulls = {str((p.get("head") or {}).get("ref")): int(p["number"]) for p in open_pulls if p.get("number")}
        anchors = await asyncio.gather(
            *(
                github.optional(f"{root}/contents/docs/proposals/PROP-{slug}/proposal.md", {"ref": base_sha})
                for slug in slugs
            )
        )
    items = []
    for slug, entry in zip(slugs, anchors, strict=True):
        runs = await runs_for(f"docs/proposals/PROP-{slug}")
        items.append(proposal_state(slug, _text(entry), branches, pulls, waiting_run(runs)))
    return {
        "base_branch": base_branch,
        "base_sha": base_sha,
        "items": items,
        "truncated": len(listing) > PROPOSAL_LIMIT,
    }
