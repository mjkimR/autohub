from typing import Annotated
from uuid import UUID

from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from fastapi import APIRouter, Depends, Query

from .schemas import SPEC_PATTERN, SddInspectionRequest, SddReadiness, SddRuntimeStatus
from .usecases import SddUseCase

router = APIRouter(prefix="/projects/{project_id}/sdd", tags=["Sdd"])


@router.get("/runs", response_model=list[PipelineRunRead])
async def spec_runs(
    project_id: UUID,
    spec_dir: Annotated[str, Query(pattern=SPEC_PATTERN, max_length=255)],
    use_case: Annotated[SddUseCase, Depends()],
):
    """The latest 20 runs bound to this project/spec, including finished executions."""
    return await use_case.runs(project_id, spec_dir)


@router.get("/runtime", response_model=SddRuntimeStatus)
async def sdd_runtime(project_id: UUID, use_case: Annotated[SddUseCase, Depends()]):
    """Whether this host can evaluate SDD runs: the runtime pin and an isolated devkit start, without a PR."""
    return await use_case.runtime(project_id)


@router.post("/readiness", response_model=SddReadiness)
async def inspect_sdd(
    project_id: UUID,
    request: SddInspectionRequest,
    use_case: Annotated[SddUseCase, Depends()],
):
    """Inspect a bound spec at a PR revision without starting work or changing Git."""
    return await use_case.readiness(project_id, request)
