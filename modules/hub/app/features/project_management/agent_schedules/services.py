from collections.abc import Sequence
from typing import Annotated
from uuid import UUID, uuid4

from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import CATALOG_SESSION_WORK_TYPES
from app.features.execution.tasks.domains.jules.service import JulesSessionPayload
from app.features.project_management.agent_schedules.models import ProjectAgentSchedule
from app.features.project_management.agent_schedules.repos import (
    SESSION_TASKS,
    AgentScheduleRepository,
    session_payload,
)
from app.features.project_management.agent_schedules.schemas import AgentScheduleWrite
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.services import ProjectService
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from fastapi import Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

RECENT_SESSIONS = 5


class AgentScheduleService:
    def __init__(
        self,
        repo: Annotated[AgentScheduleRepository, Depends()],
        projects: Annotated[ProjectService, Depends()],
        catalogs: Annotated[AICatalogRepository, Depends()],
    ) -> None:
        self.repo = repo
        self.projects = projects
        self.catalogs = catalogs

    async def list(self, session: AsyncSession, project_id: UUID) -> Sequence[ProjectAgentSchedule]:
        await self.projects.get(session, project_id)
        return await self.repo.list_for_project(session, project_id)

    async def get(self, session: AsyncSession, project_id: UUID, schedule_id: UUID) -> ProjectAgentSchedule:
        schedule = await self.repo.get(session, schedule_id)
        if schedule is None or schedule.project_id != project_id:
            raise ProjectError(404, "Agent schedule not found")
        return schedule

    async def create(self, session: AsyncSession, project_id: UUID, data: AgentScheduleWrite) -> ProjectAgentSchedule:
        project = await self.projects.get(session, project_id, lock=True)
        await self.repo.lock_catalogs(session, [data.ai_catalog_id])
        catalog = await self._catalog_for(session, project, data)
        # The owned config needs the schedule's id for its name, and the schedule needs the config's id to be
        # flushed, so the id is assigned up front and write_config flushes both in order.
        schedule = ProjectAgentSchedule(id=uuid4(), project_id=project_id, **data.model_dump())
        session.add(schedule)
        await self.repo.write_config(session, project, schedule, catalog)
        return schedule

    async def update(
        self, session: AsyncSession, project_id: UUID, schedule_id: UUID, data: AgentScheduleWrite
    ) -> ProjectAgentSchedule:
        project = await self.projects.get(session, project_id, lock=True)
        schedule = await self.get(session, project_id, schedule_id)
        previous_catalog_id = schedule.ai_catalog_id
        await self.repo.lock_catalogs(session, [previous_catalog_id, data.ai_catalog_id])
        # A schedule already on a catalog may be edited while that catalog is disabled; its entry stays paused.
        catalog = await self._catalog_for(session, project, data, keep_disabled=previous_catalog_id)
        for field, value in data.model_dump().items():
            setattr(schedule, field, value)
        await self.repo.write_config(session, project, schedule, catalog)
        return schedule

    async def delete(self, session: AsyncSession, project_id: UUID, schedule_id: UUID) -> None:
        await self.projects.get(session, project_id, lock=True)
        schedule = await self.get(session, project_id, schedule_id)
        await self.repo.delete(session, schedule)

    async def run_now(self, session: AsyncSession, project_id: UUID, schedule_id: UUID) -> ProjectAgentSchedule:
        """Make the owned schedule due on the dispatcher's next tick; the regular cadence resumes after it."""
        schedule = await self.get(session, project_id, schedule_id)
        config = await session.get(ScheduleConfig, schedule.schedule_config_id)
        if config is None:
            raise ProjectError(409, "The agent schedule's scheduler entry is missing; save it again")
        if not config.enabled:
            raise ProjectError(422, "Enable the agent schedule, its project, and its catalog before running it")
        config.next_run_at = None
        await session.flush()
        return schedule

    async def _catalog_for(
        self, session: AsyncSession, project: Project, data: AgentScheduleWrite, *, keep_disabled: UUID | None = None
    ) -> AICatalog:
        """The catalog the schedule may use; ``keep_disabled`` names the one it is on, which may be disabled."""
        if project.github_repository is None:
            raise ProjectError(422, "Connect the project to a GitHub repository before scheduling agent sessions")
        catalog = await self.catalogs.get(session, data.ai_catalog_id)
        if catalog is None:
            raise ProjectError(422, "AI catalog not found")
        if catalog.kind not in SESSION_TASKS or data.work_type not in CATALOG_SESSION_WORK_TYPES.get(catalog.kind, ()):
            raise ProjectError(422, f"AI catalog '{catalog.key}' cannot run scheduled {data.work_type} sessions")
        if not catalog.enabled and catalog.id != keep_disabled:
            raise ProjectError(422, f"AI catalog '{catalog.key}' is disabled")
        # Validate the derived payload against the task's own contract before anything is written.
        probe = ProjectAgentSchedule(project_id=project.id, **data.model_dump())
        try:
            JulesSessionPayload.model_validate(session_payload(project, probe, catalog))
        except ValidationError as exc:
            raise ProjectError(
                422, f"Agent schedule is not valid for {catalog.key}: {exc.errors()[0]['msg']}"
            ) from None
        return catalog
