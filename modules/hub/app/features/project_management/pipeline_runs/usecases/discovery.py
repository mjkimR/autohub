"""Discovery query and exact owner inspection, never execution or approval."""

from typing import Annotated

from app.features.project_management.pipeline_runs.discovery_repo import DecisionDiscoveryRepository
from app.features.project_management.pipeline_runs.discovery_service import decode_cursor, page_result
from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class DecisionDiscoveryUseCase:
    def __init__(self, repo: Annotated[DecisionDiscoveryRepository, Depends()]):
        self.repo = repo

    async def list(self, project_id, kind, question_state, cursor, limit):
        filters = {
            "project_id": str(project_id) if project_id else None,
            "kind": kind,
            "question_state": question_state,
        }
        after = decode_cursor(cursor, filters)
        async with AsyncTransaction() as session:
            if project_id and not await ProjectRepository().get(session, project_id):
                raise ProjectError(404, "Project not found")
            rows = await self.repo.page(session, project_id, kind, question_state, after, limit)
            total = await self.repo.count_actionable(session, project_id, kind, question_state)
            return page_result(rows, limit, filters, total)

    async def selection(self, key, fingerprint):
        from app.features.project_management.pipeline_runs.discovery_schemas import DecisionEntryRead

        async with AsyncTransaction() as session:
            row = await self.repo.selection(session, key)
            if not row:
                raise ProjectError(404, "Decision owner is unavailable")
            entry, run = row
            if entry.fingerprint != fingerprint:
                raise ProjectError(409, "Decision changed; reopen the current inbox")
            return DecisionEntryRead.model_validate(
                {
                    **{name: getattr(entry, name) for name in DecisionEntryRead.model_fields if hasattr(entry, name)},
                    "run_state": run.state,
                    "pull_number": run.pull_number,
                    "pull_url": run.pull_url,
                }
            )

    async def review(self, request, observer):
        runs, projects = PipelineRunRepository(), ProjectRepository()
        async with AsyncTransaction() as session:
            entry = await self.repo.entry(session, request.key)
            if not entry:
                raise ProjectError(404, "Decision is no longer available")
            run = await runs.get(session, entry.run_id)
            if not run or run.state in FINAL_RUN_STATES:
                raise ProjectError(404, "Decision owner is no longer available")
            if not entry.actionable:
                raise ProjectError(409, "Answer publication is pending; inspect the owner history")
            if entry.fingerprint != request.fingerprint:
                raise ProjectError(409, "Decision changed; review the current subject explicitly")
            project = await projects.get(session, run.project_id)
            if not project:
                raise ProjectError(404, "Project not found")
            from app.features.project_management.sdd.execution import require_current

            require_current(run)
            return PipelineRunRead.model_validate(run)
