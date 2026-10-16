"""Cloud starts of SDD activities: Hub makes the activity branch and pull request, then enrolls the run."""

from typing import Literal
from uuid import UUID

from app.features.project_management.sdd.schemas import StartActivityRequest
from app.features.project_management.sdd.usecases import SddUseCase
from app.mcp.auth import authenticated_context
from app.mcp.contracts import ProjectId, RunView
from app.mcp.dependencies import Dependencies
from app.mcp.names import catalog_keys
from app.mcp.registration import register
from app_mcp import ToolRegistry
from pydantic import Field


class StartActivity(ProjectId):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=59, description="The proposal slug of PROP-<slug>")
    request_id: UUID
    base_branch: str = Field(default="main", max_length=255, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
    activity_effort: Literal["low", "medium", "high"] | None = None
    catalog: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")


def register_sdd(registry: ToolRegistry, deps: Dependencies) -> None:
    use_case = SddUseCase(deps.project_service, deps.observer, deps.runs)

    async def start(activity: str, args: StartActivity) -> RunView:
        actor = f"machine:{(await authenticated_context()).subject}"
        request = StartActivityRequest(
            request_id=args.request_id,
            base_branch=args.base_branch,
            activity_effort=args.activity_effort,
            catalog=args.catalog,
        )
        row = await use_case.start_activity(args.project_id, activity, args.slug, request, actor)
        keys = await catalog_keys(deps)
        return RunView.model_validate(row).model_copy(update={"catalog_key": keys.get(row.ai_catalog_id)})

    async def start_planning(args: StartActivity) -> RunView:
        return await start("plan", args)

    async def start_development(args: StartActivity) -> RunView:
        return await start("dev", args)

    register(
        registry,
        "sdd_start_planning",
        "Start Planning of a draft proposal (PROP-<slug> with plan-intent recorded) in the cloud: Hub creates plan-<slug> from base_branch with a start commit that sets status reviewing, opens the pull request and enrolls the run; the first attempt is the Planning worker. An existing remote plan-<slug> refuses the start unless it carries Hub's own open pull request. Check the local branches before calling.",
        StartActivity,
        RunView,
        start_planning,
        write=True,
    )
    register(
        registry,
        "sdd_start_development",
        "Start Development of an accepted proposal in the cloud: Hub creates dev-<slug> from base_branch with an empty start commit, opens a draft pull request and enrolls a handoff-first run whose first step is devkit spec proposal handoff. An existing remote dev-<slug> refuses the start unless it carries Hub's own open pull request.",
        StartActivity,
        RunView,
        start_development,
        write=True,
    )
