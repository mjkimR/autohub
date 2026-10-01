from typing import Annotated
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.work_plans.activity_schemas import PlanActivityList, PlanActivityRead, PlanComment
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanCreate,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
)
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/projects/{project_id}/work-plans", tags=["Work Plan"])


@router.get("", response_model=WorkPlanList)
async def list_work_plans(
    project_id: UUID,
    use_case: Annotated[WorkPlanUseCase, Depends()],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    state: str | None = Query(None, pattern="^(draft|proposed|paused|active|completed|revoked)$"),
):
    return await use_case.list(project_id, offset, limit, state)


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
