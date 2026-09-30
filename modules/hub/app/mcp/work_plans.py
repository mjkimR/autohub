from uuid import UUID

from app.features.project_management.work_plans.kick import WorkPlanKick
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanCreate,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
)
from app.features.project_management.work_plans.services import WorkPlanService
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from app.mcp.contracts import Page, ProjectId
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry
from pydantic import Field, model_validator


class PlanPage(ProjectId, Page):
    pass


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


def register_work_plans(registry: ToolRegistry, deps: Dependencies) -> None:
    use_case = WorkPlanUseCase(WorkPlanService(WorkPlanRepository(), deps.runs.projects), WorkPlanKick(deps.runs))

    async def list_plans(args: PlanPage) -> WorkPlanList:
        return await use_case.list(args.project_id, args.offset, args.limit)

    async def get_plan(args: PlanLookup) -> WorkPlanRead:
        if args.plan_id is not None:
            return await use_case.get(args.project_id, args.plan_id)
        assert args.request_id is not None
        return await use_case.by_request(args.project_id, args.request_id)

    async def create(args: RegisterPlan) -> WorkPlanRead:
        return await use_case.create(args.project_id, args.plan)

    async def update(args: UpdatePlan) -> WorkPlanRead:
        return await use_case.update(args.project_id, args.plan_id, args.plan)

    async def control(args: ControlPlan) -> WorkPlanRead:
        return await use_case.control(args.project_id, args.plan_id, args.control)

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
        "Register approved work and request immediate execution. Reuse request_id and identical content after response loss; different content with the same key conflicts. Registration is not a draft or backlog operation.",
        RegisterPlan,
        WorkPlanRead,
        create,
        write=True,
    )
    register(
        registry,
        "work_plans_update",
        "Edit only wholly unstarted plans using expected_revision. Item membership is fixed. This may start newly eligible work.",
        UpdatePlan,
        WorkPlanRead,
        update,
        write=True,
    )
    register(
        registry,
        "work_plans_control",
        "Pause/resume/revoke unstarted tasks using expected_revision. Started runs continue; pause/cancel them separately. Failed or canceled tasks need inspected replacement work, not plan resume.",
        ControlPlan,
        WorkPlanRead,
        control,
        write=True,
    )
