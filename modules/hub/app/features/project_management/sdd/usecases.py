from typing import Annotated

from app.features.project_management.pipeline_runs.origin_reads import read_runs
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipelines.deps import get_pipeline_observer
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .repos import SddRepository
from .schemas import ProposalList


class SddUseCase:
    def __init__(
        self,
        projects: Annotated[ProjectService, Depends()],
        observer: Annotated[PipelineObservationService, Depends(get_pipeline_observer)],
        runs: Annotated[PipelineRunUseCase, Depends()],
    ):
        self.projects, self.observer, self.run_use_case = projects, observer, runs

    async def start_activity(self, project_id, activity, slug, request, actor: str) -> PipelineRunRead:
        from .activity_claims import ActivityClaims

        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id, lock=True)
            if project.project_type != "sdd":
                raise ProjectError(422, "Select sdd project mode first")
            if not project.enabled or not project.github_repository or not project.github_connector_id:
                raise ProjectError(422, "Enable the project and connect its GitHub repository")
            await self.run_use_case.resolve_catalog(session, project, request.catalog)
            claims = ActivityClaims(self.projects, self.observer, self.run_use_case)
            claim = await claims.reserve(session, project, activity, slug, request, actor)
            claim_id = claim.id
        return await claims.execute(project_id, claim_id)

    async def proposals(self, project_id, base_branch) -> ProposalList:
        from .proposals import list_proposals

        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            if project.project_type != "sdd":
                raise ProjectError(422, "Select sdd project mode first")
            if not project.github_repository or not project.github_connector_id:
                raise ProjectError(422, "Connect the project's GitHub repository")

        async def runs_for(unit):
            async with AsyncTransaction() as session:
                return await SddRepository().runs(session, project_id, unit)

        return ProposalList(**await list_proposals(self.observer, project, base_branch, runs_for))

    async def runs(self, project_id, spec_dir):
        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
            rows = await SddRepository().runs(session, project_id, spec_dir)
            return await read_runs(session, rows)

    async def decisions(self, run_id):
        async with AsyncTransaction() as session:
            run = await PipelineRunRepository().get(session, run_id)
            if run is None or not run.sdd_snapshot:
                raise ProjectError(404, "Native sdd run not found")
            records = await SddRepository().decisions(session, run_id)
            rows = [
                {"id": str(row.id), "created_at": row.created_at.isoformat(), **(row.decision_evidence or {})}
                for row in records
            ]
            rows.sort(key=lambda r: (r.get("revision", 0), r.get("created_at", "")), reverse=True)
            return rows

    async def retired_operation(self, project_id):
        from .execution import RETIRED_CODE, RETIRED_REASON

        async with AsyncTransaction() as session:
            await self.projects.get(session, project_id)
        raise ProjectError(410, RETIRED_REASON, code=RETIRED_CODE)
