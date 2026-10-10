from typing import Annotated
from uuid import UUID

from app.features.project_management.pipelines.deps import get_pipeline_observer
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.usecases.crud import ProjectUseCase
from app.features.project_management.repositories.schemas import (
    RepoBlobRead,
    RepoInfoRead,
    RepoTreeRead,
)
from app.features.project_management.repositories.services import RepositoryService
from fastapi import Depends


class RepositoryUseCase:
    def __init__(
        self,
        projects: Annotated[ProjectUseCase, Depends()],
        observer: Annotated[PipelineObservationService, Depends(get_pipeline_observer)],
        repo_service: Annotated[RepositoryService, Depends()],
    ):
        self.projects = projects
        self.observer = observer
        self.repo_service = repo_service

    async def get_info(self, project_id: UUID) -> RepoInfoRead:
        project, token = await self._get_context(project_id)
        assert project.github is not None
        return await self.repo_service.get_info(token, project.github.repository)

    async def get_tree(self, project_id: UUID, path: str = "", ref: str = "") -> RepoTreeRead:
        project, token = await self._get_context(project_id)
        assert project.github is not None
        return await self.repo_service.get_tree(token, project.github.repository, path=path, ref=ref)

    async def get_blob(self, project_id: UUID, path: str, ref: str = "") -> RepoBlobRead:
        project, token = await self._get_context(project_id)
        assert project.github is not None
        return await self.repo_service.get_blob(token, project.github.repository, path=path, ref=ref)

    async def _get_context(self, project_id: UUID):
        project = await self.projects.get(project_id)
        if project.github is None:
            raise ProjectError(422, "Project does not have a GitHub connection configured")
        token = await self.observer.get_token(project.github.github_connector_id, "github")
        return project, token
