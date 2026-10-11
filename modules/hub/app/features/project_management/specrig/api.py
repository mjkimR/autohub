from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from .schemas import SpecrigInspectionRequest, SpecrigReadiness
from .usecases import SpecrigUseCase

router = APIRouter(prefix="/projects/{project_id}/specrig", tags=["Specrig"])


@router.post("/readiness", response_model=SpecrigReadiness)
async def inspect_specrig(
    project_id: UUID,
    request: SpecrigInspectionRequest,
    use_case: Annotated[SpecrigUseCase, Depends()],
):
    """Inspect a bound spec at a PR revision without starting work or changing Git."""
    return await use_case.readiness(project_id, request)
