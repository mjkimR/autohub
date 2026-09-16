from typing import Annotated
from uuid import UUID

from app.features.project_management.agent_schedules.schemas import (
    AgentScheduleList,
    AgentScheduleRead,
    AgentScheduleWrite,
)
from app.features.project_management.agent_schedules.usecases import AgentScheduleUseCase
from fastapi import APIRouter, Depends, Response

router = APIRouter(prefix="/projects/{project_id}/agent-schedules", tags=["Agent Schedule"])


@router.get("", response_model=AgentScheduleList)
async def list_agent_schedules(project_id: UUID, use_case: Annotated[AgentScheduleUseCase, Depends()]):
    """A project's recurring agent sessions, each with its owned scheduler entry and recent sessions."""
    return await use_case.list(project_id)


@router.post("", response_model=AgentScheduleRead, status_code=201)
async def create_agent_schedule(
    project_id: UUID, data: AgentScheduleWrite, use_case: Annotated[AgentScheduleUseCase, Depends()]
):
    return await use_case.create(project_id, data)


@router.get("/{schedule_id}", response_model=AgentScheduleRead)
async def get_agent_schedule(project_id: UUID, schedule_id: UUID, use_case: Annotated[AgentScheduleUseCase, Depends()]):
    return await use_case.get(project_id, schedule_id)


@router.put("/{schedule_id}", response_model=AgentScheduleRead)
async def update_agent_schedule(
    project_id: UUID,
    schedule_id: UUID,
    data: AgentScheduleWrite,
    use_case: Annotated[AgentScheduleUseCase, Depends()],
):
    return await use_case.update(project_id, schedule_id, data)


@router.delete("/{schedule_id}", status_code=204)
async def delete_agent_schedule(
    project_id: UUID, schedule_id: UUID, use_case: Annotated[AgentScheduleUseCase, Depends()]
):
    await use_case.delete(project_id, schedule_id)
    return Response(status_code=204)


@router.post("/{schedule_id}/run-now", response_model=AgentScheduleRead)
async def run_agent_schedule_now(
    project_id: UUID, schedule_id: UUID, use_case: Annotated[AgentScheduleUseCase, Depends()]
):
    """Make the schedule due on the dispatcher's next tick."""
    return await use_case.run_now(project_id, schedule_id)
