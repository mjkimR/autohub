"""Publish explicit repository activity intent through GitHub, without repository execution."""

import asyncio
import base64
from urllib.parse import quote

from app.features.project_management.branches import activity_branch
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest, PipelineRunRead
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.github import WorkGitHub

from .units import _STATUS, _frontmatter_span

ACTIVITIES = {"plan": "Planning", "dev": "Development"}


def marker(activity: str, slug: str) -> str:
    return f"<!-- autohub-sdd-activity:{activity}:{slug} -->"


def _text(entry: dict | None) -> str | None:
    if not entry or entry.get("encoding") != "base64" or not isinstance(entry.get("content"), str):
        return None
    try:
        return base64.b64decode(entry["content"]).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _frontmatter_value(text: str, key: str) -> str | None:
    """Display-only metadata; it never supplies execution eligibility."""
    span = _frontmatter_span(text)
    if span is None:
        return None
    if key == "status":
        match = _STATUS.search(text, span[0], span[1])
        return match.group(1) if match else None
    for line in text[span[0] : span[1]].splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip() == key:
            return value.split("#", 1)[0].strip().strip("\"'")
    return None


async def activity_pulls(github, repository, branch):
    """Read exact candidate history before deciding whether publication is recoverable."""
    rows = []
    for page in range(1, 11):
        values = await github.reader._get_list(
            f"/repos/{repository}/pulls",
            {"head": f"{repository.split('/')[0]}:{branch}", "state": "all", "per_page": 100, "page": page},
        )
        rows.extend(p for p in values if (p.get("head") or {}).get("ref") == branch)
        if len(values) < 100:
            return rows
    raise ProjectError(409, "Activity PR history is incomplete; inspect the original candidate")


class ActivityStarter:
    def __init__(self, observer, runs):
        self.observer, self.runs = observer, runs

    async def start(
        self,
        project,
        activity,
        slug,
        request,
        actor,
        *,
        expected_base_sha=None,
        checkpoint=None,
        saved=None,
        admission=None,
    ) -> PipelineRunRead:
        if activity not in ACTIVITIES:
            raise ProjectError(422, "Activity must be plan or dev")
        try:
            branch = activity_branch(activity, slug)
        except ValueError as exc:
            raise ProjectError(422, str(exc)) from None
        unit = f"docs/proposals/PROP-{slug}"
        saved = dict(saved or {})

        async def retain(**values):
            if checkpoint:
                await checkpoint(**values)
            saved.update(values)

        repository = project.github_repository
        token = await self.observer.get_token(project.github_connector_id, "github")
        root = f"/repos/{repository}"
        async with asyncio.timeout(90), pipeline_services.create_github_client(token) as client:
            github = WorkGitHub(client)
            base = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
            if base is None:
                raise ProjectError(422, f"Base branch {request.base_branch} is not on the remote")
            base_sha = saved.get("base_sha") or base["object"]["sha"]
            if expected_base_sha and not saved.get("initial_sha") and base_sha != expected_base_sha:
                raise ProjectError(409, "Base SHA changed before activity publication")
            existing = await github.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}")
            pulls = await activity_pulls(github, repository, branch)
            known = saved.get("pull_number")
            if known is not None:
                pull = await github.optional(f"{root}/pulls/{known}")
                if pull is None:
                    raise ProjectError(409, "Recorded activity PR is absent; reconcile the retained candidate")
                pulls = [pull]
            owned = [
                pull
                for pull in pulls
                if marker(activity, slug) in (pull.get("body") or "")
                and (pull.get("base") or {}).get("ref") == request.base_branch
                and (pull.get("head") or {}).get("ref") == branch
                and ((pull.get("head") or {}).get("repo") or {}).get("full_name") == repository
                and ((pull.get("base") or {}).get("repo") or {}).get("full_name") == repository
            ]
            if len(owned) > 1:
                raise ProjectError(409, "Activity PR outcome is ambiguous; inspect retained candidates")
            pull = owned[0] if owned else None
            initial = saved.get("initial_sha")
            if existing and (not initial or existing["object"]["sha"] != initial):
                raise ProjectError(409, "Activity branch has a different owner or head", code="SDD_BRANCH_EXISTS")
            if pull and (not initial or (pull.get("head") or {}).get("sha") != initial):
                raise ProjectError(409, "Activity PR does not match the retained candidate")
            if pull and pull.get("state") != "open":
                raise ProjectError(409, "Recorded activity PR already closed; no replacement is created")
            if known is not None and (pull is None or pull.get("number") != known):
                raise ProjectError(409, "Recorded activity PR identity changed")
            if existing is None:
                if saved.get("ref_attempted"):
                    raise ProjectError(409, "Original activity ref outcome is uncertain; inspect before reconciliation")
                if pull is not None:
                    raise ProjectError(409, "Recorded activity branch is missing; no replacement is created")
                if initial is None:
                    commit = await github.reader._get(f"{root}/git/commits/{base_sha}")
                    created = await github.write(
                        "POST",
                        f"{root}/git/commits",
                        {
                            "message": f"Start {ACTIVITIES[activity]} of PROP-{slug}\n\nAutoHub request: {request.request_id}",
                            "tree": commit["tree"]["sha"],
                            "parents": [base_sha],
                        },
                    )
                    initial = created["sha"]
                    # An empty intent commit makes a PR openable without editing repository files.
                    await retain(initial_sha=initial, branch=branch, base_sha=base_sha)
                latest = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
                if not latest or latest["object"]["sha"] != base_sha:
                    raise ProjectError(409, "Base moved before activity publication")
                await retain(ref_attempted=True)
                await github.write("POST", f"{root}/git/refs", {"ref": f"refs/heads/{branch}", "sha": initial})
                await retain(ref_published=True)
            if pull is None:
                if saved.get("pr_attempted"):
                    raise ProjectError(409, "Original activity PR outcome is uncertain; inspect before reconciliation")
                await retain(pr_attempted=True)
                pull = await github.write(
                    "POST",
                    f"{root}/pulls",
                    {
                        "title": f"{ACTIVITIES[activity]}: PROP-{slug}",
                        "head": branch,
                        "base": request.base_branch,
                        "draft": True,
                        "body": f"{ACTIVITIES[activity]} of PROP-{slug}. Follow this repository's instructions. "
                        f"Repository setup and workflow are the working agent's responsibility.\n\n{marker(activity, slug)}",
                    },
                )
            number = pull["number"]
            await retain(pull_number=number)
        enrollment = EnrollPullRequest(
            pull_number=number,
            spec_dir=unit,
            activity_effort=request.activity_effort,
            catalog=request.catalog,
            handoff=activity == "dev",
        )
        if saved.get("enrollment_request"):
            previous = EnrollPullRequest.model_validate(saved["enrollment_request"])
            if previous != enrollment:
                raise ProjectError(409, "Saved enrollment intent differs from the original request")
        else:
            await retain(enrollment_request=enrollment.model_dump(mode="json"))
        return await self.runs.enroll(project.id, enrollment, **({"admission": admission} if admission else {}))
