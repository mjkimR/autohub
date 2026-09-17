from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.schemas import AICatalogSessionRead
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.agent_schedules.schemas import (
    AgentScheduleList,
    AgentScheduleRead,
    AgentScheduleWrite,
)
from app.features.project_management.agent_schedules.services import RECENT_SESSIONS, AgentScheduleService
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AgentScheduleUseCase:
    def __init__(
        self,
        service: Annotated[AgentScheduleService, Depends()],
        catalogs: Annotated[AICatalogRepository, Depends()],
    ) -> None:
        self.service = service
        self.catalogs = catalogs

    async def _read_all(
        self, session: AsyncSession, schedules: Sequence[ProjectAgentSchedule]
    ) -> list[AgentScheduleRead]:
        """Merge each schedule with its owned entry and recent sessions, loading both sets in one query each."""
        for schedule in schedules:
            await session.refresh(schedule)
        config_ids = [schedule.schedule_config_id for schedule in schedules]
        configs = {
            config.id: config
            for config in (await session.scalars(select(ScheduleConfig).where(ScheduleConfig.id.in_(config_ids)))).all()
        }
        recent = await self.catalogs.list_recent_sessions_for_schedules(session, config_ids, RECENT_SESSIONS)
        items = []
        for schedule in schedules:
            config = configs.get(schedule.schedule_config_id)
            items.append(
                AgentScheduleRead.model_validate(schedule).model_copy(
                    update={
                        "task_func": config.task_func if config is not None else "",
                        "next_run_at": config.next_run_at if config is not None else None,
                        "last_run_at": config.last_run_at if config is not None else None,
                        "recent_sessions": [
                            AICatalogSessionRead.model_validate(row)
                            for row in recent.get(schedule.schedule_config_id, [])
                        ],
                    }
                )
            )
        return items

    async def _read(self, session: AsyncSession, schedule: ProjectAgentSchedule) -> AgentScheduleRead:
        [item] = await self._read_all(session, [schedule])
        return item

    async def list(self, project_id: UUID) -> AgentScheduleList:
        async with AsyncTransaction() as session:
            rows = await self.service.list(session, project_id)
            return AgentScheduleList(items=await self._read_all(session, rows))

    async def get(self, project_id: UUID, schedule_id: UUID) -> AgentScheduleRead:
        async with AsyncTransaction() as session:
            return await self._read(session, await self.service.get(session, project_id, schedule_id))

    async def create(self, project_id: UUID, data: AgentScheduleWrite) -> AgentScheduleRead:
        async with AsyncTransaction() as session:
            return await self._read(session, await self.service.create(session, project_id, data))

    async def update(self, project_id: UUID, schedule_id: UUID, data: AgentScheduleWrite) -> AgentScheduleRead:
        async with AsyncTransaction() as session:
            return await self._read(session, await self.service.update(session, project_id, schedule_id, data))

    async def delete(self, project_id: UUID, schedule_id: UUID) -> None:
        async with AsyncTransaction() as session:
            await self.service.delete(session, project_id, schedule_id)

    async def run_now(self, project_id: UUID, schedule_id: UUID) -> AgentScheduleRead:
        async with AsyncTransaction() as session:
            return await self._read(session, await self.service.run_now(session, project_id, schedule_id))
