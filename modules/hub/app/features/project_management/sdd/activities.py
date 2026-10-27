"""Starting an activity in the cloud (strategy layer 01 sections 6.2, 6.3 and 7.3).

Planning: ``plan-<slug>`` from the base, a start commit that sets the draft proposal to ``reviewing``, a ready pull
request and a run whose first attempt is the Planning worker. Development: ``dev-<slug>`` from the base, an empty
start commit, a draft pull request and a run whose first step is ``devkit spec proposal handoff``. Both refuse an
existing remote branch; Hub's own open pull request on it is enrolled again instead (recovery after a lost response).
"""

import asyncio
import base64
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from app.features.project_management.branches import activity_branch
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest, PipelineRunRead
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.github import WorkGitHub

from .checkout import checkout, command, push_head
from .plan_decisions import commit_identity
from .policy import planning_intent
from .units import _STATUS, _frontmatter_span, set_status

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
    span = _frontmatter_span(text)
    if span is None:
        return None
    if key == "status":
        match = _STATUS.search(text, span[0], span[1])
        return match.group(1) if match else None
    for line in text[span[0] : span[1]].splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip() == key:
            return value.split("#", 1)[0].strip().strip("'\"")
    return None


async def start_branch(
    repository: str, base_sha: str, branch: str, token: str, message: tuple[str, str], write: Callable | None
) -> str:
    """Create ``branch`` at ``base_sha`` plus one start commit (``write`` edits the checkout; none means empty)."""
    name, email = commit_identity()
    try:
        async with asyncio.timeout(90):
            async with checkout(repository, base_sha, base_sha, token) as root:
                if write is not None:
                    write(root)
                await command("git-safe", "add", "-A", cwd=root)
                await command(
                    "git-safe",
                    "-c",
                    f"user.name={name}",
                    "-c",
                    f"user.email={email}",
                    "commit",
                    "--quiet",
                    "--allow-empty",
                    "-m",
                    message[0],
                    "-m",
                    message[1],
                    cwd=root,
                )
                sha = (await command("git-safe", "rev-parse", "HEAD", cwd=root)).strip()
                await push_head(root, repository, branch, None, token)
    except (OSError, TimeoutError):
        raise ProjectError(422, "SDD runner unavailable or timed out; provision Git and the pinned CLI") from None
    return sha


class ActivityStarter:
    """Create the branch and pull request of an activity, then enroll its run; GitHub reads and writes only."""

    def __init__(self, observer, runs):
        self.observer, self.runs = observer, runs

    async def start(self, project, activity: str, slug: str, request, actor: str) -> PipelineRunRead:
        if activity not in ACTIVITIES:
            raise ProjectError(422, "Activity must be plan or dev")
        try:
            branch = activity_branch(activity, slug)
        except ValueError as exc:
            raise ProjectError(422, str(exc)) from None
        unit = f"docs/proposals/PROP-{slug}"
        repository, connector = project.github_repository, project.github_connector_id
        token = await self.observer.get_token(connector, "github")
        root = f"/repos/{repository}"
        async with asyncio.timeout(150), pipeline_services.create_github_client(token) as client:
            github = WorkGitHub(client)
            base = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
            if base is None:
                raise ProjectError(422, f"Base branch {request.base_branch} is not on the remote")
            base_sha = base["object"]["sha"]
            existing = await github.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}")
            pulls = await github.reader._get_list(
                f"{root}/pulls", {"head": f"{repository.split('/')[0]}:{branch}", "state": "open", "per_page": 100}
            )
            pull = next((p for p in pulls if p.get("head", {}).get("ref") == branch), None)
            if existing is not None:
                if pull is None or marker(activity, slug) not in (pull.get("body") or ""):
                    raise ProjectError(
                        409,
                        f"Branch {branch} already exists on the remote; enroll its pull request to attach it instead",
                        code="SDD_BRANCH_EXISTS",
                    )
                number = pull["number"]  # Hub's own start whose response was lost: enroll it again
                anchor = _text(await github.optional(f"{root}/contents/{unit}/proposal.md", {"ref": base_sha}))
            else:
                anchor = _text(await github.optional(f"{root}/contents/{unit}/proposal.md", {"ref": base_sha}))
                if anchor is None:
                    raise ProjectError(422, f"PROP-{slug} is not on {request.base_branch}")
                status = _frontmatter_value(anchor, "status")
                if activity == "plan":
                    if status != "draft":
                        raise ProjectError(
                            409, f"PROP-{slug} is {status or 'without a status'}; Planning starts from a draft"
                        )
                    if _frontmatter_value(anchor, "needs_decompose") == "true":
                        raise ProjectError(409, f"PROP-{slug} needs decomposition in Backlog before Planning")
                    if not await planning_intent(repository, base_sha, token, unit):
                        raise ProjectError(409, f"Record plan-intent for PROP-{slug} in Backlog before Planning")
                    message = (f"Start Planning of PROP-{slug}", f"Started-by: {actor}")

                    def write(checkout_root: Path) -> None:
                        set_status(checkout_root, unit, "draft", "reviewing")

                    sha = await start_branch(repository, base_sha, branch, token, message, write)
                elif status != "accepted":
                    raise ProjectError(
                        409,
                        f"PROP-{slug} is {status or 'without a status'}; Development starts from an accepted proposal",
                    )
                else:
                    message = (
                        f"Start Development of PROP-{slug}",
                        f"Handoff follows as the first step.\nStarted-by: {actor}",
                    )
                    sha = await start_branch(repository, base_sha, branch, token, message, None)
                body = (
                    f"{ACTIVITIES[activity]} of PROP-{slug} on `{branch}` from `{request.base_branch}` ({base_sha[:12]}). "
                    + (
                        "The Cloud Agent reviews the proposal here; Hub records the acceptance or rejection."
                        if activity == "plan"
                        else "The first step is `devkit spec proposal handoff`; the spec workflow follows."
                    )
                    + f"\n\n{marker(activity, slug)}"
                )
                created = await github.write(
                    "POST",
                    f"{root}/pulls",
                    {
                        "title": f"{ACTIVITIES[activity]}: PROP-{slug}",
                        "head": branch,
                        "base": request.base_branch,
                        "draft": activity == "dev",
                        "body": body,
                    },
                )
                number = created["number"]
                assert sha  # the start commit is what the pull request shows
        if request.activity_effort is None:
            value = _frontmatter_value(anchor or "", "planning_effort" if activity == "plan" else "dev_effort")
            if value in ("low", "medium", "high"):
                request = request.model_copy(update={"activity_effort": value})
        return await self.runs.enroll(
            project.id,
            EnrollPullRequest(
                pull_number=number,
                spec_dir=unit,
                activity_effort=request.activity_effort,
                catalog=request.catalog,
                handoff=activity == "dev",
            ),
        )
