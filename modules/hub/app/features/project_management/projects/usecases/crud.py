from typing import Annotated
from uuid import UUID

from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.schemas import ProjectList, ProjectPatch, ProjectRead, ProjectWrite
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends
from sqlalchemy.exc import IntegrityError


class ProjectUseCase:
    def __init__(self, service: Annotated[ProjectService, Depends()]):
        self.service = service

    async def list(self, offset: int, limit: int, search: str = "") -> ProjectList:
        async with AsyncTransaction() as session:
            rows, total = await self.service.repo.get_multi(session, offset, limit, search)
            return ProjectList(items=[ProjectRead.model_validate(row) for row in rows], total_count=total)

    async def get(self, project_id: UUID) -> ProjectRead:
        async with AsyncTransaction() as session:
            return ProjectRead.model_validate(await self.service.get(session, project_id))

    async def get_by_repository(self, repository: str) -> ProjectRead:
        async with AsyncTransaction() as session:
            matches = await self.service.repo.conflicts(session, repository.strip().lower())
            if not matches:
                raise ProjectError(404, "No project is connected to this repository")
            return ProjectRead.model_validate(matches[0])

    async def create(self, data: ProjectWrite) -> ProjectRead:
        try:
            async with AsyncTransaction() as session:
                return ProjectRead.model_validate(await self.service.create(session, data))
        except IntegrityError:
            raise ProjectError(409, "Project mapping conflicts or a connector was removed; reload and retry") from None

    async def patch(self, project_id: UUID, data: ProjectPatch) -> ProjectRead:
        try:
            async with AsyncTransaction() as session:
                return ProjectRead.model_validate(await self.service.patch(session, project_id, data))
        except IntegrityError:
            raise ProjectError(409, "Project mapping conflicts or a connector was removed; reload and retry") from None

    async def delete(self, project_id: UUID) -> None:
        async with AsyncTransaction() as session:
            await self.service.delete(session, project_id)

    async def import_schedule(self, schedule_id: UUID) -> ProjectRead:
        try:
            async with AsyncTransaction() as session:
                return ProjectRead.model_validate(await self.service.import_schedule(session, schedule_id))
        except IntegrityError:
            raise ProjectError(409, "Project mapping changed during import; nothing was migrated") from None
