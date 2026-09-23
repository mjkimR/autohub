from typing import Annotated
from uuid import UUID

from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
    WorkPlanWrite,
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
):
    return await use_case.list(project_id, offset, limit)


@router.post("", response_model=WorkPlanRead, status_code=201)
async def create_work_plan(project_id: UUID, data: WorkPlanWrite, use_case: Annotated[WorkPlanUseCase, Depends()]):
    """Atomically register work; ready items start in this request (the tick finishes the rest), without approval."""
    return await use_case.create(project_id, data)


@router.get("/{plan_id}", response_model=WorkPlanRead)
async def get_work_plan(project_id: UUID, plan_id: UUID, use_case: Annotated[WorkPlanUseCase, Depends()]):
    return await use_case.get(project_id, plan_id)


@router.put("/{plan_id}", response_model=WorkPlanRead)
async def update_work_plan(
    project_id: UUID,
    plan_id: UUID,
    data: WorkPlanUpdate,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    return await use_case.update(project_id, plan_id, data)


@router.post("/{plan_id}/control", response_model=WorkPlanRead)
async def control_work_plan(
    project_id: UUID,
    plan_id: UUID,
    data: PlanControl,
    use_case: Annotated[WorkPlanUseCase, Depends()],
):
    """Pause/resume/revoke unstarted work only; started PR runs continue through merging."""
    return await use_case.control(project_id, plan_id, data)
