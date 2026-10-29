"""The Proposals screen: each proposal's state on the base, its activity branches and the decisions it can take.

The base holds the proposal's own status; a ``plan-<slug>`` branch shows a draft as ``reviewing`` without a base commit
(strategy layer 01 section 5.1). The actions follow 01 sections 6.2 and 6.3: start Planning of a draft, accept or
reject a reviewing proposal through its waiting run, start Development of an accepted one. A rejected proposal takes
no action; it waits for the hygiene cleanup of a local Host. A draft that devkit-spec's decomposition gate refuses
(``needs_decompose`` or a size other than S, M or L) offers no Planning start, and a repository whose
``[development] approach`` is incubation offers neither a start nor an acceptance (devkit-spec refuses them).
"""

import asyncio
from urllib.parse import quote

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.github import WorkGitHub

from .activities import _frontmatter_value, _text
from .gates import PLAN_ACCEPT_REQUEST
from .policy import INCUBATION, LIFECYCLE_INACTIVE, development_approach, size_blocker
from .progress import held

PROPOSAL_LIMIT = 50


def _slug(name: str) -> str | None:
    slug = name.removeprefix("PROP-")
    return slug if name.startswith("PROP-") and slug and slug[0].isalnum() and slug == slug.lower() else None


def recorded_approach(runs) -> str | None:
    """The ``[development] approach`` the latest run evaluation recorded, ``None`` before any evaluation.

    Incubation when either the Planning head (where devkit-spec accepts) or the owning base (where Development
    hands off) chose it. A hint for which actions to offer; starts and acceptances read the policy again.
    """
    for run in runs:
        progress = run.sdd_progress or {}
        policies = [
            policy
            for policy in (
                progress.get("base_policy"),
                (progress.get("snapshot") or {}).get("policy"),
                (run.sdd_snapshot or {}).get("policy"),
            )
            if isinstance(policy, dict) and policy
        ]
        if policies:
            return INCUBATION if any(development_approach(p) == INCUBATION for p in policies) else "sdd"
    return None


def waiting_run(runs) -> dict | None:
    """The latest unfinished run of the proposal unit, with what a decision on it needs."""
    run = next((r for r in runs if r.state not in FINAL_RUN_STATES), None)
    if run is None:
        return None
    progress = run.sdd_progress or {}
    requests = (progress.get("current") or {}).get("requests") or []
    return {
        "id": str(run.id),
        "state": run.state,
        "revision": run.revision,
        "pause_reason": run.pause_reason,
        "pull_number": run.pull_number,
        "head_sha": progress.get("head_sha"),
        "plan_accept_open": run.state in ("paused", "blocked")
        and progress.get("unit_status") == "reviewing"
        and not held(progress)
        and any(r.get("id") == PLAN_ACCEPT_REQUEST for r in requests),
        "decided": bool(progress.get("plan_decision")),
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
    display = "reviewing" if status == "draft" and plan else status
    actions: list[str] = []
    note = None
    size = size_blocker(_frontmatter_value(anchor or "", "size"))
    if status == "rejected":
        note = "Planning ended by rejection; a local Host removes it in hygiene after writing its ADR"
    elif approach == INCUBATION:
        note = LIFECYCLE_INACTIVE
    elif status == "draft" and not plan:
        if _frontmatter_value(anchor or "", "needs_decompose") == "true":
            note = "Needs decomposition in Backlog before Planning"
        elif size:
            note = f"The proposal is {size}; decompose it in Backlog before Planning (S, M or L)"
        else:
            actions.append("start_planning")
    elif status == "accepted" and not dev:
        actions.append("start_development")
    if run and run["plan_accept_open"] and status != "rejected":
        actions += ["reject"] if approach == INCUBATION else ["accept", "reject"]
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
        items.append(proposal_state(slug, _text(entry), branches, pulls, waiting_run(runs), recorded_approach(runs)))
    return {
        "base_branch": base_branch,
        "base_sha": base_sha,
        "items": items,
        "truncated": len(listing) > PROPOSAL_LIMIT,
    }
