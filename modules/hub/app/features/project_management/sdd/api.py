from typing import Annotated
from uuid import UUID

from app.auth import CurrentUser
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from fastapi import APIRouter, Depends, Path, Query

from . import batch_models  # noqa: F401 -- register durable batch metadata
from .batch_schemas import BatchRead, ControlBatch
from .batch_usecases import SddBatchUseCase
from .claim_history import SddClaimHistory
from .schemas import (
    SPEC_PATTERN,
    ClaimRead,
    ProposalList,
    ReconcileClaimRequest,
    ReconcileRunRequest,
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
    """Request Planning: publish a Draft PR and enroll ordinary repository-owned work."""
    return await use_case.start_activity(project_id, "plan", slug, request, f"user:{user.id}")


@router.post("/proposals/{slug}/development", response_model=PipelineRunRead, status_code=201)
async def start_development(
    project_id: UUID,
    slug: Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=59)],
    request: StartActivityRequest,
    user: CurrentUser,
    use_case: Annotated[SddUseCase, Depends()],
):
    """Request Development: publish a Draft PR and enroll ordinary repository-owned work."""
    return await use_case.start_activity(project_id, "dev", slug, request, f"user:{user.id}")


@router.get("/runtime", deprecated=True)
@router.post("/readiness", deprecated=True)
@router.get("/milestones", deprecated=True)
@router.post("/milestone-preview", deprecated=True)
@router.post("/batches", deprecated=True)
async def retired_sdd_evaluation(project_id: UUID, use_case: Annotated[SddUseCase, Depends()]):
    """Embedded evaluation and executable native batches have been retired."""
    return await use_case.retired_operation(project_id)


@router.get("/batches", response_model=list[BatchRead])
async def list_batches(project_id: UUID, use_case: Annotated[SddBatchUseCase, Depends()]):
    return await use_case.lists(project_id)


@router.get("/batches/{batch_id}", response_model=BatchRead)
async def get_batch(project_id: UUID, batch_id: UUID, use_case: Annotated[SddBatchUseCase, Depends()]):
    return await use_case.get(project_id, batch_id)


@router.post("/batches/{batch_id}/controls", response_model=BatchRead)
async def control_batch(
    project_id: UUID,
    batch_id: UUID,
    request: ControlBatch,
    user: CurrentUser,
    use_case: Annotated[SddBatchUseCase, Depends()],
):
    return await use_case.control(project_id, batch_id, request, f"user:{user.id}")


@router.get("/claims/{claim_id}", response_model=ClaimRead)
async def get_claim(
    project_id: UUID,
    claim_id: UUID,
    use_case: Annotated[SddClaimHistory, Depends()],
):
    return await use_case.get(project_id, claim_id)


@router.post("/claims/{claim_id}/reconcile", response_model=ClaimRead)
async def reconcile_claim(
    project_id: UUID,
    claim_id: UUID,
    request: ReconcileClaimRequest,
    user: CurrentUser,
    use_case: Annotated[SddClaimHistory, Depends()],
):
    """Acknowledge inspected external work and release only this retired reservation."""
    return await use_case.reconcile(project_id, claim_id, request, f"user:{user.id}")


@router.post("/runs/{run_id}/reconcile", response_model=PipelineRunRead)
async def reconcile_retired_run(
    project_id: UUID,
    run_id: UUID,
    request: ReconcileRunRequest,
    user: CurrentUser,
    use_case: Annotated[SddClaimHistory, Depends()],
):
    """Acknowledge retired external work without resuming the retained Run."""
    return await use_case.reconcile_run(project_id, run_id, request, f"user:{user.id}")
