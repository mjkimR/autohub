from typing import Annotated

from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipelines.deps import get_pipeline_observer
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .repos import SpecrigRepository
from .schemas import SpecrigReadiness
from .services import SpecrigService


class SpecrigUseCase:
    def __init__(
        self,
        projects: Annotated[ProjectService, Depends()],
        observer: Annotated[PipelineObservationService, Depends(get_pipeline_observer)],
    ):
        self.projects, self.observer = projects, observer

    async def readiness(self, project_id, request):
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            if project.project_type != "specrig":
                return SpecrigReadiness(ready=False, reason="Select specrig project mode first")
            repository, connector = project.github_repository, project.github_connector_id
            if not repository or not connector or not project.enabled:
                return SpecrigReadiness(ready=False, reason="Enable the project and connect its GitHub repository")
        try:
            pull = await self.observer.get_pull_request(connector, repository, request.pull_number)
            if pull.get("state") != "open":
                return SpecrigReadiness(ready=False, reason="Select an open pull request")
            token = await self.observer.get_token(connector, "github")
            evidence = await SpecrigService().inspect(repository, request.spec_dir, pull, token)
            return SpecrigReadiness(
                ready=True,
                head_sha=evidence["head_sha"],
                base_sha=evidence["base_sha"],
                cli_version=evidence["snapshot"]["cli_version"],
                workflow=evidence["workflow"],
                current=evidence["current"],
            )
        except ProjectError as exc:
            return SpecrigReadiness(ready=False, reason=str(exc))

    async def decisions(self, run_id):
        async with AsyncTransaction() as session:
            run = await PipelineRunRepository().get(session, run_id)
            if run is None or not run.specrig_snapshot:
                raise ProjectError(404, "Native specrig run not found")
            records = await SpecrigRepository().decisions(session, run_id)
            rows = [
                {"id": str(row.id), "created_at": row.created_at.isoformat(), **(row.decision_evidence or {})}
                for row in records
            ]
            rows.sort(key=lambda r: (r.get("revision", 0), r.get("created_at", "")), reverse=True)
            return rows
