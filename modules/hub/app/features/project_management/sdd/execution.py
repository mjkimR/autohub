"""Descriptive activity intent and the permanent legacy-execution boundary."""

from app.features.project_management.projects.errors import ProjectError

EXECUTION_VERSION = 2
RETIRED_CODE = "SDD_EXECUTION_RETIRED"
RETIRED_REASON = "Native SDD evaluation was retired; inspect external work before registering replacement work"


def optimistic(run) -> bool:
    snapshot = getattr(run, "sdd_snapshot", None) or {}
    return snapshot.get("execution_version") == EXECUTION_VERSION


def retired(run) -> bool:
    return bool(getattr(run, "sdd_snapshot", None)) and not optimistic(run)


def require_current(run) -> None:
    if retired(run):
        raise ProjectError(410, RETIRED_REASON, code=RETIRED_CODE)


async def reject_unreconciled_replacement(session, project_id, pull_number, admission=None) -> None:
    """Local cancellation never acknowledges that previously dispatched work stopped."""
    from app.features.project_management.pipeline_runs.models import PipelineRun
    from app.features.project_management.sdd.batch_models import SddActivityClaim
    from sqlalchemy import or_, select

    claim = await session.scalar(
        select(SddActivityClaim.id)
        .outerjoin(PipelineRun, PipelineRun.id == SddActivityClaim.run_id)
        .where(
            SddActivityClaim.project_id == project_id,
            ~SddActivityClaim.settled,
            or_(
                SddActivityClaim.checkpoint["retired"].as_boolean().is_(True),
                SddActivityClaim.checkpoint["execution_version"].as_integer() == EXECUTION_VERSION,
            ),
            SddActivityClaim.id != admission[0] if admission else True,
            or_(
                PipelineRun.pull_number == pull_number,
                SddActivityClaim.checkpoint["pull_number"].as_integer() == pull_number,
            ),
        )
        .limit(1)
    )
    if claim is not None:
        raise ProjectError(
            409,
            f"Activity claim {claim} retains external work; inspect its owner and explicitly reconcile uncertainty before replacement",
            code="SDD_RECONCILIATION_REQUIRED",
        )

    previous = await session.scalar(
        select(PipelineRun.id)
        .where(
            PipelineRun.project_id == project_id,
            PipelineRun.pull_number == pull_number,
            PipelineRun.sdd_progress["retirement"]["external_work_unreconciled"].as_boolean().is_(True),
        )
        .limit(1)
    )
    if previous is not None:
        raise ProjectError(
            409,
            f"Retired run {previous} retains external work; inspect and explicitly reconcile it before replacement",
            code="SDD_RECONCILIATION_REQUIRED",
        )
