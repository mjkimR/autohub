from typing import Annotated
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from fastapi import APIRouter, Depends, Path, Query

from .schemas import (
    SPEC_PATTERN,
    ProposalList,
    SddInspectionRequest,
    SddReadiness,
    SddRuntimeStatus,
    StartActivityRequest,
)
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


@router.get("/proposals", response_model=ProposalList)
async def list_proposals(
    project_id: UUID,
    use_case: Annotated[SddUseCase, Depends()],
    base_branch: Annotated[
        str, Query(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
    ] = "main",
):
    """Proposals on the base with their activity branches, waiting run and the actions they can take."""
    return await use_case.proposals(project_id, base_branch)


@router.post("/proposals/{slug}/planning", response_model=PipelineRunRead, status_code=201)
async def start_planning(
    project_id: UUID,
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=59)],
    request: StartActivityRequest,
    user: CurrentUser,
    use_case: Annotated[SddUseCase, Depends()],
):
    """Start Planning of a draft proposal: Hub creates plan-<slug> and its pull request, then enrolls the run."""
    return await use_case.start_activity(project_id, "plan", slug, request, f"user:{user.id}")


@router.post("/proposals/{slug}/development", response_model=PipelineRunRead, status_code=201)
async def start_development(
    project_id: UUID,
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=59)],
    request: StartActivityRequest,
    user: CurrentUser,
    use_case: Annotated[SddUseCase, Depends()],
):
    """Start Development of an accepted proposal: dev-<slug>, a draft pull request, a handoff-first run."""
    return await use_case.start_activity(project_id, "dev", slug, request, f"user:{user.id}")


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
