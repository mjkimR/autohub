"""One bounded advancement loop for scheduler, webhook, and interactive callers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.schemas import (
    LeaseMutation,
    LeaseRequest,
    PipelineRunRead,
    PrepareImplementationAttempt,
)
from app.features.project_management.pipeline_runs.usecases.delivery import CATALOG_HOLD_CODE
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.utils.time_util import get_current_utc_time

if TYPE_CHECKING:
    from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase

ADVANCE_SECONDS = 90
ADVANCE_MAX_STEPS = 8
ADVANCE_LEASE_SECONDS = 120


def progress_key(run: PipelineRunRead) -> tuple:
    """Only workflow changes justify another observation, never timestamps or a revision alone."""
    native = run.sdd_progress or {}
    stage = (native.get("current") or {}).get("stage") or {}
    return (
        run.state,
        stage.get("id"),
        bool(native.get("approval")),
        native.get("integrated"),
        native.get("head_sha"),
        native.get("base_sha"),
    )


class PipelineRunAdvancement:
    def __init__(self, lifecycle: PipelineRunUseCase):
        self.lifecycle = lifecycle

    async def advance_until_wait(
        self,
        run_id: UUID,
        observer: PipelineObservationService,
        *,
        owner: str | None = None,
        respect_due: bool = False,
    ) -> PipelineRunRead:
        """Events may refresh an observation early; delivery delays always remain binding."""
        owner = owner or f"advance:{uuid4().hex[:8]}"
        grant = await self.lifecycle.acquire_lease(run_id, LeaseRequest(owner=owner, ttl_seconds=ADVANCE_LEASE_SECONDS))
        try:
            async with asyncio.timeout(ADVANCE_SECONDS):
                run = await self.lifecycle.get(run_id)
                observed = False
                for step in range(ADVANCE_MAX_STEPS):
                    if (
                        run.next_action_at is not None
                        and as_utc(run.next_action_at) > get_current_utc_time()
                        and (
                            respect_due
                            or step > 0
                            or run.state in (PipelineRunState.QUEUED, PipelineRunState.DISPATCHING)
                        )
                    ):
                        return run
                    if run.state == PipelineRunState.QUEUED:
                        await self.lifecycle.prepare_implementation(
                            run_id,
                            PrepareImplementationAttempt(
                                owner=owner, token=grant.token, expected_run_revision=run.revision
                            ),
                        )
                        run = await self.lifecycle.get(run_id)
                        continue
                    if run.state == PipelineRunState.DISPATCHING:
                        try:
                            # A delivery starts external work. Do not poll it immediately afterward.
                            return await self.lifecycle.dispatch_implementation(run_id, owner=owner, token=grant.token)
                        except ProjectError as exc:
                            if exc.code != CATALOG_HOLD_CODE or not observed:
                                raise
                            return run
                    approval_wait = run.state == PipelineRunState.PAUSED and (run.sdd_progress or {}).get(
                        "waiting_for_approval"
                    )
                    if (
                        run.state not in (PipelineRunState.IMPLEMENTING, PipelineRunState.AWAITING_CI)
                        and not approval_wait
                    ):
                        return run
                    before = progress_key(run)
                    run = await self.lifecycle.observe_run(run_id, owner=owner, token=grant.token, observer=observer)
                    observed = True
                    if progress_key(run) == before:
                        return run
                return run
        except TimeoutError:
            raise ProjectError(
                504, "Pipeline advancement exceeded its time budget; reconcile on the next tick"
            ) from None
        finally:
            await self.lifecycle.release_lease(run_id, LeaseMutation(owner=owner, token=grant.token))
