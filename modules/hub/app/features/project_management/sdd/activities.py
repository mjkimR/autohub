"""Starting an activity in the cloud (strategy layer 01 sections 6.2, 6.3 and 7.3).

Planning: ``plan-<slug>`` from the base, a start commit that sets the draft proposal to ``reviewing``, a ready pull
request and a run whose first attempt is the Planning worker. Development: ``dev-<slug>`` from the base, an empty
start commit, a draft pull request and a run whose first step is ``devkit spec proposal handoff``. Both refuse an
existing remote branch; Hub's own open pull request on it is enrolled again instead (recovery after a lost response).
Before writing anything, both read the base through devkit: an ``adaptive-dev`` development approach refuses them, and
Planning also needs devkit-spec's size gate (S, M, L or no size) and a recorded plan-intent.
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
from .policy import LIFECYCLE_INACTIVE, size_blocker, start_blocker
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
    repository: str,
    base_sha: str,
    branch: str,
    token: str,
    message: tuple[str, str],
    write: Callable | None,
    *,
    checkpoint=None,
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
                if checkpoint:
                    await checkpoint(initial_sha=sha, branch=branch, base_sha=base_sha)
                await push_head(root, repository, branch, None, token)
    except (OSError, TimeoutError):
        raise ProjectError(422, "SDD runner unavailable or timed out; provision Git and the pinned CLI") from None
    return sha


def admission_reason(anchor: str, activity: str, slug: str) -> str | None:
    """Shared pure admission, preserving individual start's status/decomposition gates."""
    status = _frontmatter_value(anchor, "status")
    if activity == "plan":
        if status != "draft":
            return f"PROP-{slug} is {status or 'without a status'}; Planning starts from a draft"
        if _frontmatter_value(anchor, "needs_decompose") == "true":
            return f"PROP-{slug} needs decomposition in Backlog before Planning"
        if size := size_blocker(_frontmatter_value(anchor, "size")):
            return f"PROP-{slug} is {size}; decompose it in Backlog before Planning (S, M or L)"
    elif status != "accepted":
        return f"PROP-{slug} is {status or 'without a status'}; Development starts from an accepted proposal"
    return None


def _code(reason: str) -> str | None:
    return "SDD_LIFECYCLE_INACTIVE" if reason == LIFECYCLE_INACTIVE else None


class ActivityStarter:
    """Create the branch and pull request of an activity, then enroll its run; GitHub reads and writes only."""

    def __init__(self, observer, runs):
        self.observer, self.runs = observer, runs

    async def start(
        self,
        project,
        activity: str,
        slug: str,
        request,
        actor: str,
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
        repository, connector = project.github_repository, project.github_connector_id
        token = await self.observer.get_token(connector, "github")
        root = f"/repos/{repository}"
        async with asyncio.timeout(150), pipeline_services.create_github_client(token) as client:
            github = WorkGitHub(client)
            base = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
            if base is None:
                raise ProjectError(422, f"Base branch {request.base_branch} is not on the remote")
            base_sha = base["object"]["sha"]
            saved = saved or {}
            existing = await github.optional(f"{root}/git/ref/heads/{quote(branch, safe='')}")
            known_pr = saved.get("pull_number") if checkpoint else None
            initial = saved.get("initial_sha") if checkpoint else None
            if known_pr is not None:
                pull = await github.optional(f"{root}/pulls/{known_pr}")
                if pull is None or pull.get("state") != "open":
                    raise ProjectError(
                        409,
                        "Recorded native pull request is missing or closed; retain its exact identity without replacement",
                    )
            else:
                from .milestones import activity_pulls

                pulls = await activity_pulls(github, repository, branch, state="all" if initial else "open")
                if checkpoint and initial:
                    owned = {
                        p["number"]: p
                        for p in pulls
                        if (p.get("head") or {}).get("ref") == branch
                        and (p.get("head") or {}).get("sha") == initial
                        and ((p.get("head") or {}).get("repo") or {}).get("full_name") == repository
                        and (p.get("base") or {}).get("ref") == request.base_branch
                        and ((p.get("base") or {}).get("repo") or {}).get("full_name") == repository
                        and marker(activity, slug) in (p.get("body") or "")
                    }
                    if len(owned) > 1:
                        raise ProjectError(
                            409, "Native pull request outcome is ambiguous; preserve the exact candidate"
                        )
                    pull = next(iter(owned.values()), None)
                    if pull:
                        await checkpoint(pull_number=pull["number"])
                        if pull.get("state") != "open":
                            raise ProjectError(
                                409, "Recorded native candidate already has a closed pull request; no replacement"
                            )
                else:
                    pull = next((p for p in pulls if (p.get("head") or {}).get("ref") == branch), None)
            if checkpoint and existing is None and (initial or known_pr is not None):
                raise ProjectError(
                    409,
                    "Recorded native branch is absent; reconcile the saved candidate without creating replacement artifacts",
                )

            async def candidate_checkpoint(**values):
                assert checkpoint is not None
                latest = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
                if not latest or latest["object"]["sha"] != base_sha:
                    raise ProjectError(409, "Base moved before native branch publication")
                await checkpoint(**values)

            if existing is not None and checkpoint:
                initial = saved.get("initial_sha")
                known_pr = saved.get("pull_number")
                if not initial or (pull is None and existing["object"]["sha"] != initial):
                    raise ProjectError(409, "Existing native branch has no exact durable admission ownership")
                if pull is not None and (
                    (known_pr is not None and pull["number"] != known_pr)
                    or (pull.get("base") or {}).get("ref") != request.base_branch
                    or (pull.get("head") or {}).get("sha") != initial
                    or ((pull.get("head") or {}).get("repo") or {}).get("full_name") != repository
                    or ((pull.get("base") or {}).get("repo") or {}).get("full_name") != repository
                ):
                    raise ProjectError(409, "Native PR does not match the saved admission claim")
                if pull is None:
                    created = await github.write(
                        "POST",
                        f"{root}/pulls",
                        {
                            "title": f"{ACTIVITIES[activity]}: PROP-{slug}",
                            "head": branch,
                            "base": request.base_branch,
                            "draft": activity == "dev",
                            "body": f"Recovered exact native admission.\n\n{marker(activity, slug)}",
                        },
                    )
                    pull = created
                    await checkpoint(pull_number=pull["number"])
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
                if checkpoint and pull is not None:
                    raise ProjectError(409, "An existing pull request is not owned by this fresh admission claim")
                if expected_base_sha and base_sha != expected_base_sha:
                    raise ProjectError(409, "Native admission base SHA changed; re-evaluate before claiming")
                if checkpoint:
                    await checkpoint(expected_sha=base_sha)
                anchor = _text(await github.optional(f"{root}/contents/{unit}/proposal.md", {"ref": base_sha}))
                if anchor is None:
                    raise ProjectError(422, f"PROP-{slug} is not on {request.base_branch}")
                if reason := admission_reason(anchor, activity, slug):
                    raise ProjectError(409, reason)
                if activity == "plan":
                    if reason := await start_blocker(repository, base_sha, token, unit, activity):
                        raise ProjectError(409, reason, code=_code(reason))
                    if checkpoint:
                        latest = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
                        if not latest or latest["object"]["sha"] != base_sha:
                            raise ProjectError(409, "Base moved during native policy evaluation")
                        await checkpoint(admission_base=base_sha)
                    message = (f"Start Planning of PROP-{slug}", f"Started-by: {actor}")

                    def write(checkout_root: Path) -> None:
                        set_status(checkout_root, unit, "draft", "reviewing")

                    sha = await start_branch(
                        repository,
                        base_sha,
                        branch,
                        token,
                        message,
                        write,
                        **({"checkpoint": candidate_checkpoint} if checkpoint else {}),
                    )
                else:
                    if reason := await start_blocker(repository, base_sha, token, unit, activity):
                        raise ProjectError(409, reason, code=_code(reason))
                    if checkpoint:
                        latest = await github.optional(f"{root}/git/ref/heads/{quote(request.base_branch, safe='')}")
                        if not latest or latest["object"]["sha"] != base_sha:
                            raise ProjectError(409, "Base moved during native policy evaluation")
                        await checkpoint(admission_base=base_sha)
                    message = (
                        f"Start Development of PROP-{slug}",
                        f"Handoff follows as the first step.\nStarted-by: {actor}",
                    )
                    sha = await start_branch(
                        repository,
                        base_sha,
                        branch,
                        token,
                        message,
                        None,
                        **({"checkpoint": candidate_checkpoint} if checkpoint else {}),
                    )
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
                if checkpoint:
                    await checkpoint(pull_number=number)
                assert sha  # the start commit is what the pull request shows
        if request.activity_effort is None:
            value = _frontmatter_value(anchor or "", "planning_effort" if activity == "plan" else "dev_effort")
            if value in ("low", "medium", "high"):
                request = request.model_copy(update={"activity_effort": value})
        enrollment = EnrollPullRequest(
            pull_number=number,
            spec_dir=unit,
            activity_effort=request.activity_effort,
            catalog=request.catalog,
            handoff=activity == "dev",
        )
        if saved and saved.get("enrollment_request"):
            enrollment = EnrollPullRequest.model_validate(saved["enrollment_request"])
            if (
                enrollment.pull_number != number
                or enrollment.spec_dir != unit
                or enrollment.handoff != (activity == "dev")
            ):
                raise ProjectError(409, "Saved native enrollment intent does not match exact artifacts")
        elif checkpoint:
            await checkpoint(enrollment_request=enrollment.model_dump(mode="json"))
        return await self.runs.enroll(project.id, enrollment, **({"admission": admission} if admission else {}))
