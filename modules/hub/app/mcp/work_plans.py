from typing import Literal
from uuid import UUID

from app.features.project_management.work_plans.activity_schemas import PlanActivityList, PlanActivityRead, PlanComment
from app.features.project_management.work_plans.grouping import GroupFilter
from app.features.project_management.work_plans.kick import WorkPlanKick
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanCreate,
    WorkPlanGroupUpdate,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
)
from app.features.project_management.work_plans.services import WorkPlanService
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from app.mcp.auth import authenticated_context
from app.mcp.contracts import Page, ProjectId
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry
from pydantic import Field, model_validator


class PlanPage(ProjectId, Page):
    state: Literal["draft", "proposed", "paused", "active", "completed", "revoked"] | None = None
    group_key: GroupFilter = None


class PlanLookup(ProjectId):
    plan_id: UUID | None = None
    request_id: UUID | None = None

    @model_validator(mode="after")
    def one_identifier(self):
        if (self.plan_id is None) == (self.request_id is None):
            raise ValueError("Provide plan_id or registration request_id, but not both")
        return self


class Registration(WorkPlanCreate):
    request_id: UUID = Field(description="Generate once and reuse with identical content on retries")


class RegisterPlan(ProjectId):
    plan: Registration


class UpdatePlan(ProjectId):
    plan_id: UUID
    plan: WorkPlanUpdate


class ControlPlan(ProjectId):
    plan_id: UUID
    control: PlanControl


class SetPlanGroup(ProjectId):
    plan_id: UUID
    group: WorkPlanGroupUpdate


class ActivityPage(ProjectId, Page):
    plan_id: UUID
    comments_only: bool = False


class CommentPlan(ProjectId):
    plan_id: UUID
    comment: PlanComment


def register_work_plans(registry: ToolRegistry, deps: Dependencies) -> None:
    use_case = WorkPlanUseCase(WorkPlanService(WorkPlanRepository(), deps.runs.projects), WorkPlanKick(deps.runs))

    async def list_plans(args: PlanPage) -> WorkPlanList:
        return await use_case.list(args.project_id, args.offset, args.limit, args.state, args.group_key)

    async def get_plan(args: PlanLookup) -> WorkPlanRead:
        if args.plan_id is not None:
            return await use_case.get(args.project_id, args.plan_id)
        assert args.request_id is not None
        return await use_case.by_request(args.project_id, args.request_id)

    async def create(args: RegisterPlan) -> WorkPlanRead:
        return await use_case.create(args.project_id, args.plan, f"machine:{(await authenticated_context()).subject}")

    async def update(args: UpdatePlan) -> WorkPlanRead:
        return await use_case.update(
            args.project_id, args.plan_id, args.plan, f"machine:{(await authenticated_context()).subject}"
        )

    async def control(args: ControlPlan) -> WorkPlanRead:
        return await use_case.control(
            args.project_id, args.plan_id, args.control, f"machine:{(await authenticated_context()).subject}"
        )

    async def set_group(args: SetPlanGroup) -> WorkPlanRead:
        return await use_case.set_group(
            args.project_id, args.plan_id, args.group, f"machine:{(await authenticated_context()).subject}"
        )

    async def activity(args: ActivityPage) -> PlanActivityList:
        return await use_case.activity(args.project_id, args.plan_id, args.offset, args.limit, args.comments_only)

    async def comment(args: CommentPlan) -> PlanActivityRead:
        return await use_case.comment(
            args.project_id, args.plan_id, args.comment, f"machine:{(await authenticated_context()).subject}"
        )

    register(
        registry,
        "work_plans_activity",
        "Read paginated Plan comments and before/after changes; no execution.",
        ActivityPage,
        PlanActivityList,
        activity,
    )
    register(
        registry,
        "work_plans_comment",
        "Append context only, never execution input. Reuse request_id after response loss.",
        CommentPlan,
        PlanActivityRead,
        comment,
        write=True,
    )

    register(
        registry,
        "work_plans_set_group",
        "Change or clear classification using expected_revision, including started/finished plans. Does not start, pause or isolate work. Registration retries never overwrite the current group.",
        SetPlanGroup,
        WorkPlanRead,
        set_group,
        write=True,
    )
    register(
        registry,
        "work_plans_list",
        "List plans, tasks, dependencies, run links and outbound Issue status for one project.",
        PlanPage,
        WorkPlanList,
        list_plans,
    )
    register(
        registry,
        "work_plans_get",
        "Read a plan by plan_id or recover registration using request_id. Does not start work.",
        PlanLookup,
        WorkPlanRead,
        get_plan,
    )
    register(
        registry,
        "work_plans_register",
        "Create a draft seed (zero/incomplete items allowed), proposed work for review, paused ready work, or active work for execution (default). Only active starts, respecting scheduled_at, dependencies and capacity. Reuse request_id with identical content after response loss.",
        RegisterPlan,
        WorkPlanRead,
        create,
        write=True,
    )
    register(
        registry,
        "work_plans_update",
        "Edit wholly unstarted plans using expected_revision. Draft/proposed allow membership changes; proposed edits return to draft. Active/paused membership is fixed. Only active edits may start work.",
        UpdatePlan,
        WorkPlanRead,
        update,
        write=True,
    )
    register(
        registry,
        "work_plans_control",
        "Control using expected_revision: propose submits a complete draft; draft withdraws a proposal; ready validates and holds draft/proposed; resume explicitly authorizes execution; pause holds active work; revoke withdraws. Started runs continue. Failed tasks need inspected replacement work.",
        ControlPlan,
        WorkPlanRead,
        control,
        write=True,
    )
