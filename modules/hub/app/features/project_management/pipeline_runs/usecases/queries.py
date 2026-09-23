"""Read models for runs and their execution history; no delivery or state transitions."""

from datetime import UTC
from typing import Annotated
from uuid import UUID

from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    ExecutionAttemptList,
    ExecutionAttemptRead,
    ExecutionDeliveryRead,
    ExecutionReplyRead,
    PipelineRunList,
    PipelineRunRead,
    PipelineRunSummary,
)
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends


class PipelineRunQueries:
    def __init__(self, repo: Annotated[PipelineRunRepository, Depends()]):
        self.repo = repo

    async def list_runs(
        self,
        project_id: UUID | None,
        offset: int,
        limit: int,
        state: PipelineRunState | None = None,
        search: str = "",
        pull_number: int | None = None,
    ) -> PipelineRunList:
        async with AsyncTransaction() as session:
            rows, total = await self.repo.list(
                session,
                project_id=project_id,
                offset=offset,
                limit=limit,
                state=state,
                search=search,
                pull_number=pull_number,
            )
            return PipelineRunList(items=[PipelineRunRead.model_validate(row) for row in rows], total_count=total)

    async def get(self, run_id: UUID) -> PipelineRunRead:
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            return PipelineRunRead.model_validate(run)

    async def list_attempts(self, run_id: UUID, *, offset: int = 0, limit: int | None = None) -> ExecutionAttemptList:
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id)
            if run is None:
                raise ProjectError(404, "Pipeline run not found")
            rows = await self.repo.list_attempts(session, run_id, offset=offset, limit=limit)
            started_at = run.created_at.replace(tzinfo=UTC) if run.created_at.tzinfo is None else run.created_at
            # A final state is the last thing written to a run, so its last update is when it ended.
            finished_at = (
                (run.updated_at.replace(tzinfo=UTC) if run.updated_at.tzinfo is None else run.updated_at)
                if run.state in FINAL_RUN_STATES
                else None
            )
            kinds = await self.repo.attempt_counts(session, run_id)
            return ExecutionAttemptList(
                items=[ExecutionAttemptRead.model_validate(row) for row in rows],
                total_count=sum(kinds.values()),
                summary=PipelineRunSummary(
                    attempts_by_kind=kinds,
                    requests_sent=await self.repo.count_requests_sent(session, run_id),
                    quota_limit_replies=await self.repo.count_quota_limit_replies(session, run_id),
                    started_at=started_at,
                    finished_at=finished_at,
                    elapsed_seconds=int(((finished_at or get_current_utc_time()) - started_at).total_seconds()),
                ),
            )

    async def list_deliveries(self, run_id: UUID, attempt_id: UUID) -> list[ExecutionDeliveryRead]:
        async with AsyncTransaction() as session:
            attempt = await self.repo.get_attempt(session, attempt_id)
            if attempt is None or attempt.pipeline_run_id != run_id:
                raise ProjectError(404, "Execution attempt not found for this pipeline run")
            return [
                ExecutionDeliveryRead.model_validate(row)
                for row in await self.repo.list_deliveries(session, attempt_id)
            ]

    async def list_replies(self, run_id: UUID, attempt_id: UUID) -> list[ExecutionReplyRead]:
        async with AsyncTransaction() as session:
            attempt = await self.repo.get_attempt(session, attempt_id)
            if attempt is None or attempt.pipeline_run_id != run_id:
                raise ProjectError(404, "Execution attempt not found for this pipeline run")
            return [ExecutionReplyRead.model_validate(row) for row in await self.repo.list_replies(session, attempt_id)]
