"""Best-effort progression after the caller's durable mutation has committed."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app_layer_base.core.log import logger

if TYPE_CHECKING:
    from .lifecycle import PipelineRunUseCase

PROMPT_SECONDS = 10


async def advance_promptly(lifecycle: PipelineRunUseCase, run: PipelineRunRead) -> PipelineRunRead:
    try:
        async with asyncio.timeout(PROMPT_SECONDS):
            return await lifecycle.advance_until_wait(run.id, lifecycle.observer, respect_due=True)
    except Exception:
        # Registration/resume succeeded. Its durable state, not a second request, owns recovery.
        logger.info(f"PR run {run.id} immediate progression deferred to the scheduler")
    try:
        return await lifecycle.get(run.id)
    except Exception:
        return run
