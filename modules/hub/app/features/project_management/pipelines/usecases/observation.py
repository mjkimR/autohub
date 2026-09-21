from typing import Annotated
from uuid import UUID

from app.features.project_management.pipelines.repos import PipelineObservationRepository
from app.features.project_management.pipelines.schemas import PipelineObservation, PipelineObservationConfig
from app.features.project_management.pipelines.services import (
    OBSERVATION_TASK,
    PipelineConfigurationError,
    PipelineObservationQueryService,
    PipelineObservationService,
)
from app.features.project_management.projects.observation import resolve_project_observation
from app.features.project_management.projects.repos import PROJECT_OBSERVATION_TASK, ProjectRepository
from app.features.project_management.projects.schemas import ProjectObservationPayload
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class InspectPipelineUseCase:
    def __init__(self, service: Annotated[PipelineObservationService, Depends()]):
        self.service = service

    async def execute(self, config: PipelineObservationConfig) -> PipelineObservation:
        return await self.service.observe(config)


class GetPipelineObservationUseCase:
    def __init__(self, service: Annotated[PipelineObservationQueryService, Depends()]):
        self.service = service

    async def execute(self, schedule_id: UUID) -> PipelineObservation | None:
        return await self.service.get(schedule_id)


class ObservePipelineUseCase:
    """Observe outside the write transaction, then verify the configuration before saving."""

    def __init__(
        self,
        service: Annotated[PipelineObservationService, Depends()],
        repo: Annotated[PipelineObservationRepository, Depends()],
    ):
        self.service = service
        self.repo = repo

    async def observe_and_save(self, config: PipelineObservationConfig, schedule_id: UUID) -> PipelineObservation:
        report = await self.service.observe(config)
        async with AsyncTransaction() as session:
            schedule = await self.repo.get_schedule(session, schedule_id)
            if schedule is None or schedule.task_func != OBSERVATION_TASK:
                raise PipelineConfigurationError("Observation schedule no longer exists")
            if PipelineObservationConfig.model_validate(schedule.payload) != config:
                raise PipelineConfigurationError("Observation configuration changed during execution")
            await self.repo.save(session, schedule_id, report.model_dump(mode="json"))
        return report

    async def observe_project_and_save(
        self, payload: ProjectObservationPayload, schedule_id: UUID
    ) -> PipelineObservation:
        config, revision = await resolve_project_observation(payload)
        report = await self.service.observe(config)
        async with AsyncTransaction() as session:
            project = await ProjectRepository().get(session, payload.project_id, lock=True)
            schedule = await self.repo.get_schedule(session, schedule_id)
            if (
                project is None
                or not project.enabled
                or project.revision != revision
                or schedule is None
                or schedule.task_func != PROJECT_OBSERVATION_TASK
                or ProjectObservationPayload.model_validate(schedule.payload) != payload
            ):
                raise PipelineConfigurationError("Project or schedule changed during observation")
            await self.repo.save(session, schedule_id, report.model_dump(mode="json"))
        return report
