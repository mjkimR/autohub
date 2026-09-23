"""Start follow-up work in the request that made it possible instead of waiting for the next scheduler tick.

Cloud Run only guarantees CPU while a request is open, so this runs inside that request under a time budget.
Anything left unfinished, refused, or failed stays due and the scheduler tick completes it as before.
"""

import asyncio
from typing import Annotated
from uuid import UUID

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.execution import WorkPlanExecution
from app.features.project_management.work_plans.models import WorkItem
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from fastapi import Depends
from sqlalchemy import select

# Well inside the 60-second request timeout; one item's preparation alone may take up to 45 seconds.
KICK_BUDGET_SECONDS = 25
KICK_ADMIT_LIMIT = 2


class WorkPlanKick:
    def __init__(self, lifecycle: Annotated[PipelineRunUseCase, Depends()]):
        self.lifecycle = lifecycle
        self.execution = WorkPlanExecution(lifecycle.observer)

    async def run(self, project_id: UUID, *, run_id: UUID | None = None) -> None:
        """Admit and dispatch ready items; with `run_id`, first observe that run's item so a merge releases dependents.

        Never raises: the caller's own result is already committed.
        """
        try:
            async with asyncio.timeout(KICK_BUDGET_SECONDS):
                if run_id is not None and not await self.execution.observe_run(project_id, run_id):
                    return
                admitted = await self.execution.advance_phase(project_id, "admit", limit=KICK_ADMIT_LIMIT)
                for queued in await self._queued_runs(admitted):
                    try:
                        await self.lifecycle.manual_advance(queued, self.lifecycle.observer)
                    except ProjectError as exc:
                        # e.g. a quota hold or a lease held by the tick; the run stays queued for it.
                        logger.info(f"Work run {queued} first dispatch deferred: {exc.detail}")
        except Exception as exc:
            logger.warning(f"Immediate work plan follow-up for project {project_id} deferred to the tick: {exc!r}")

    @staticmethod
    async def _queued_runs(item_ids: list[UUID]) -> list[UUID]:
        if not item_ids:
            return []
        async with AsyncTransaction() as session:
            return list(
                await session.scalars(
                    select(PipelineRun.id)
                    .join(WorkItem, WorkItem.pipeline_run_id == PipelineRun.id)
                    .where(WorkItem.id.in_(item_ids), PipelineRun.state == "queued")
                )
            )
