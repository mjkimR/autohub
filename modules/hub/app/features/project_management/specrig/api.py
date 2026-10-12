from typing import Annotated
from uuid import UUID

from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from fastapi import APIRouter, Depends, Query

from .schemas import SPEC_PATTERN, SpecrigInspectionRequest, SpecrigReadiness
from .usecases import SpecrigUseCase

router = APIRouter(prefix="/projects/{project_id}/specrig", tags=["Specrig"])


@router.get("/runs", response_model=list[PipelineRunRead])
async def spec_runs(
    project_id: UUID,
    spec_dir: Annotated[str, Query(pattern=SPEC_PATTERN, max_length=255)],
    use_case: Annotated[SpecrigUseCase, Depends()],
):
    """The latest 20 runs bound to this project/spec, including finished executions."""
    return await use_case.runs(project_id, spec_dir)


@router.post("/readiness", response_model=SpecrigReadiness)
async def inspect_specrig(
    project_id: UUID,
    request: SpecrigInspectionRequest,
    use_case: Annotated[SpecrigUseCase, Depends()],
):
    """Inspect a bound spec at a PR revision without starting work or changing Git."""
    return await use_case.readiness(project_id, request)
