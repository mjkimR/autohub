"""Protect saved activity artifacts from duplicate enrollment."""

from app.features.project_management.projects.errors import ProjectError


async def reject_unreconciled_replacement(session, project_id, pull_number, admission=None, *, branch=None) -> None:
    """Fence saved candidate identity even before its PR publication response is recorded."""
    from app.features.project_management.pipeline_runs.models import PipelineRun
    from app.features.project_management.sdd.claim_models import SddActivityClaim
    from sqlalchemy import or_, select

    identities = [
        PipelineRun.pull_number == pull_number,
        SddActivityClaim.checkpoint["pull_number"].as_integer() == pull_number,
    ]
    if branch is not None:
        identities.append(SddActivityClaim.checkpoint["branch"].as_string() == branch)
    statement = (
        select(SddActivityClaim.id)
        .outerjoin(PipelineRun, PipelineRun.id == SddActivityClaim.run_id)
        .where(
            SddActivityClaim.project_id == project_id,
            ~SddActivityClaim.settled,
            or_(*identities),
        )
    )
    if admission:
        statement = statement.where(SddActivityClaim.id != admission[0])
    claim = await session.scalar(statement.limit(1))
    if claim is not None:
        raise ProjectError(
            409,
            f"Activity claim {claim} retains external work; inspect /api/v1/projects/{project_id}/sdd/claims/{claim} "
            "and explicitly reconcile uncertainty before replacement",
            code="SDD_RECONCILIATION_REQUIRED",
        )
