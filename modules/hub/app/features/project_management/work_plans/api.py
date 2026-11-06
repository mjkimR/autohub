from typing import Annotated
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.activity_schemas import PlanActivityList, PlanActivityRead, PlanComment
from app.features.project_management.work_plans.grouping import GroupFilter
from app.features.project_management.work_plans.recovery_schemas import WorkItemRecover, WorkItemRecoveryList
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkItemRecoveryResult,
    WorkPlanCreate,
    WorkPlanGroupUpdate,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
)
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/projects/{project_id}/work-plans", tags=["Work Plan"])


@router.get("", response_model=WorkPlanList)
async def list_work_plans(
    project_id: UUID,
    use_case: Annotated[WorkPlanUseCase, Depends()],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    state: str | None = Query(None, pattern="^(draft|proposed|paused|active|completed|revoked)$"),
    group_key: GroupFilter = None,
):
    return await use_case.list(project_id, offset, limit, state, group_key)


@router.post("", response_model=WorkPlanRead, status_code=201)
async def create_work_plan(
    project_id: UUID, data: WorkPlanCreate, user: CurrentUser, use_case: Annotated[WorkPlanUseCase, Depends()]
):
    """Create a seed/proposal/held plan, or register active work for immediate eligibility."""
    return await use_case.create(project_id, data, f"user:{user.id}")


@router.get("/{plan_id}", response_model=WorkPlanRead)
async def get_work_plan(project_id: UUID, plan_id: UUID, use_case: Annotated[WorkPlanUseCase, Depends()]):
    return await use_case.get(project_id, plan_id)


@router.put("/{plan_id}", response_model=WorkPlanRead)
async def update_work_plan(
    project_id: UUID,
    plan_id: UUID,
    data: WorkPlanUpdate,
    user: CurrentUser,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    return await use_case.update(project_id, plan_id, data, f"user:{user.id}")


@router.post("/{plan_id}/control", response_model=WorkPlanRead)
async def control_work_plan(
    project_id: UUID,
    plan_id: UUID,
    data: PlanControl,
    user: CurrentUser,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    """Pause/resume/revoke unstarted work only; started PR runs continue through merging."""
    return await use_case.control(project_id, plan_id, data, f"user:{user.id}")


@router.patch("/{plan_id}/group", response_model=WorkPlanRead)
async def set_work_plan_group(
    project_id: UUID,
    plan_id: UUID,
    data: WorkPlanGroupUpdate,
    user: CurrentUser,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    """Change classification at any lifecycle stage without starting or controlling execution."""
    return await use_case.set_group(project_id, plan_id, data, f"user:{user.id}")


@router.get("/registrations/{request_id}", response_model=WorkPlanRead)
async def get_registered_plan(project_id: UUID, request_id: UUID, use_case: Annotated[WorkPlanUseCase, Depends()]):
    return await use_case.by_request(project_id, request_id)


@router.get("/{plan_id}/activity", response_model=PlanActivityList)
async def list_plan_activity(
    project_id: UUID,
    plan_id: UUID,
    use_case: Annotated[WorkPlanUseCase, Depends()],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    comments_only: bool = False,
):
    return await use_case.activity(project_id, plan_id, offset, limit, comments_only)


@router.post("/{plan_id}/comments", response_model=PlanActivityRead, status_code=201)
async def add_plan_comment(
    project_id: UUID,
    plan_id: UUID,
    data: PlanComment,
    user: CurrentUser,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    return await use_case.comment(project_id, plan_id, data, f"user:{user.id}")


@router.post("/{plan_id}/items/{item_id}/recover", response_model=WorkItemRecoveryResult)
async def recover_work_item(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    data: WorkItemRecover,
    user: CurrentUser,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    return await use_case.recover(project_id, plan_id, item_id, data, f"user:{user.id}")


@router.get("/{plan_id}/items/{item_id}/recoveries", response_model=WorkItemRecoveryList)
async def work_item_recoveries(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    use_case: Annotated[WorkPlanUseCase, Depends()],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return await use_case.recoveries(project_id, plan_id, item_id, offset, limit)


from app.features.project_management.work_plans.replacement_schemas import (  # noqa: E402
    ReplacementAcceptCommand,
    ReplacementLinkCommand,
    ReplacementRead,
    ReplacementWithdrawCommand,
)
from app.features.project_management.work_plans.replacement_usecase import ReplacementUseCase  # noqa: E402


@router.get("/{plan_id}/items/{item_id}/replacement-links", response_model=ReplacementRead)
async def replacement_links(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    use_case: Annotated[ReplacementUseCase, Depends()],
    replacement_item_id: UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    event_link_id: UUID | None = None,
    event_offset: int = Query(0, ge=0),
):
    return await use_case.get(
        project_id, plan_id, item_id, replacement_item_id, offset, limit, event_link_id, event_offset
    )


async def replacement_mutation(use_case, *args):
    # Preserve the owning application's detail envelope; code identifies only
    # this feature's authoritative transaction refusal for exact-request replay.
    try:
        return await use_case.mutate(*args)
    except ProjectError as exc:
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail, "code": exc.code})


@router.post("/{plan_id}/items/{item_id}/replacement-links", response_model=ReplacementRead)
async def link_replacement(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    data: ReplacementLinkCommand,
    user: CurrentUser,
    use_case: Annotated[ReplacementUseCase, Depends()],
):
    return await replacement_mutation(use_case, project_id, plan_id, item_id, "link", data, f"user:{user.id}")


@router.post("/{plan_id}/items/{item_id}/replacement-links/{link_id}/acceptances", response_model=ReplacementRead)
async def accept_replacement(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    link_id: UUID,
    data: ReplacementAcceptCommand,
    user: CurrentUser,
    use_case: Annotated[ReplacementUseCase, Depends()],
):
    return await replacement_mutation(
        use_case, project_id, plan_id, item_id, "accept", data, f"user:{user.id}", link_id
    )


@router.post("/{plan_id}/items/{item_id}/replacement-links/{link_id}/withdraw", response_model=ReplacementRead)
async def withdraw_replacement(
    project_id: UUID,
    plan_id: UUID,
    item_id: UUID,
    link_id: UUID,
    data: ReplacementWithdrawCommand,
    user: CurrentUser,
    use_case: Annotated[ReplacementUseCase, Depends()],
):
    return await replacement_mutation(
        use_case, project_id, plan_id, item_id, "withdraw", data, f"user:{user.id}", link_id
    )
