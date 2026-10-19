from typing import Annotated

from app.features.project_management.branches import unit_branch_mismatch
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipelines.deps import get_pipeline_observer
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends

from .profiles import runtime_scope
from .repos import SddRepository
from .schemas import ProposalList, SddReadiness, SddRuntimeStatus
from .services import SddService


class SddUseCase:
    def __init__(
        self,
        projects: Annotated[ProjectService, Depends()],
        observer: Annotated[PipelineObservationService, Depends(get_pipeline_observer)],
        runs: Annotated[PipelineRunUseCase, Depends()],
    ):
        self.projects, self.observer, self.run_use_case = projects, observer, runs

    async def start_activity(self, project_id, activity, slug, request, actor: str) -> PipelineRunRead:
        from .activities import ActivityStarter

        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            if project.project_type != "sdd":
                raise ProjectError(422, "Select sdd project mode first")
            if not project.enabled or not project.github_repository or not project.github_connector_id:
                raise ProjectError(422, "Enable the project and connect its GitHub repository")
        return await ActivityStarter(self.observer, self.run_use_case).start(project, activity, slug, request, actor)

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
            return [PipelineRunRead.model_validate(row) for row in rows]

    async def runtime(self, project_id):
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
        with runtime_scope(project.github_repository):
            return SddRuntimeStatus(**await SddService().runtime_status())

    async def readiness(self, project_id, request):
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            if project.project_type != "sdd":
                return SddReadiness(ready=False, reason="Select sdd project mode first")
            repository, connector = project.github_repository, project.github_connector_id
            if not repository or not connector or not project.enabled:
                return SddReadiness(ready=False, reason="Enable the project and connect its GitHub repository")
        try:
            pull = await self.observer.get_pull_request(connector, repository, request.pull_number)
            if pull.get("state") != "open":
                return SddReadiness(ready=False, reason="Select an open pull request")
            if mismatch := unit_branch_mismatch(request.spec_dir, str((pull.get("head") or {}).get("ref", ""))):
                return SddReadiness(ready=False, reason=mismatch)
            token = await self.observer.get_token(connector, "github")
            evidence = await SddService().inspect(repository, request.spec_dir, pull, token)
            if evidence.get("unit_status") == "rejected":
                return SddReadiness(
                    ready=False, reason="Rejected proposal: its Planning has ended and hygiene removes it"
                )
            return SddReadiness(
                ready=True,
                head_sha=evidence["head_sha"],
                base_sha=evidence["base_sha"],
                cli_version=evidence["snapshot"]["cli_version"],
                workflow=evidence["workflow"],
                current=evidence["current"],
                warnings=evidence.get("warnings", []),
            )
        except ProjectError as exc:
            return SddReadiness(ready=False, reason=str(exc))

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
