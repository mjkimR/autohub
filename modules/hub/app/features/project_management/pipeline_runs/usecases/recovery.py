"""Guarded Work Item terminal entry; ordinary resume intentionally remains unchanged."""

from uuid import uuid4

from app.features.project_management.pipeline_runs.models import ExecutionAttempt, ExecutionDelivery
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.requests import build_implementation_request, request_digest
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest
from app.features.project_management.pipeline_runs.usecases.transitions import EXTERNAL_IMPLEMENTATION_STATUS, as_utc
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.utils.time_util import get_current_utc_time


async def activate_recovery(session, run, item, recovery, pull, *, implemented, stopped):
    """Caller holds Project/Plan/catalog/Run/Item locks and verified the recovery lease."""
    repo = PipelineRunRepository()
    now = get_current_utc_time()
    if (
        item.pipeline_run_id != run.id
        or recovery.item_id != item.id
        or recovery.state not in ("accepted", "reconciling", "awaiting-admission")
    ):
        raise ProjectError(409, "Recovery no longer owns this Work Item")
    if run.state not in ("failed", "canceled") or run.revision != recovery.accepted_run_revision:
        raise ProjectError(409, "Run changed during recovery")
    if run.lease_expires_at and as_utc(run.lease_expires_at) > now:
        raise ProjectError(409, "Prior Run owner has not stopped")
    owner = await repo.get_active_for_pull(session, run.project_id, run.pull_number)
    if owner is not None:
        raise ProjectError(409, "Another active Run owns the PR", code="ACTIVE_RUN_CONFLICT")
    attempts = await repo.list_attempts(session, run.id)
    if not implemented:
        if not stopped:
            raise ProjectError(409, "Prior delivery is not definitively stopped")
        current = [a for a in attempts if a.epoch == run.epoch]
        deliveries = []
        for attempt in current:
            deliveries.extend(await repo.list_deliveries(session, attempt.id))
        silent = sum(d.cause in ("silent", "recovery") for d in deliveries)
        if (
            sum(a.kind == "ci-fix" for a in current) >= 2
            or sum(a.kind == "conflict-fix" for a in current) >= 1
            or silent >= 1
        ):
            raise ProjectError(409, "Automatic budget exhausted; inspect Run", code="RECOVERY_BUDGET_EXHAUSTED")
    if await repo.active_attempt(session, run.id) is not None:
        raise ProjectError(409, "Prior attempt remains active")
    key = uuid4()
    if attempts:
        prior = ImplementationRequest.model_validate(attempts[-1].request_snapshot)
    else:
        prior, _, _ = build_implementation_request(run, run.github_repository)
    request = prior.model_copy(
        update={
            "correlation_marker": f"hub-attempt:{key}",
            "pull_request": prior.pull_request.model_copy(update={"head_sha": pull["head"]["sha"]}),
        }
    )
    snapshot = request.model_dump(mode="json")
    attempt = await repo.create_attempt(
        session,
        ExecutionAttempt(
            pipeline_run_id=run.id,
            attempt_number=await repo.next_attempt_number(session, run.id),
            epoch=run.epoch,
            kind=prior.kind,
            state="running" if implemented else "planned",
            request_snapshot=snapshot,
            request_digest=request_digest(snapshot),
            idempotency_key=key,
            external_status=EXTERNAL_IMPLEMENTATION_STATUS if implemented else None,
            started_at=now if implemented else None,
        ),
    )
    if not implemented:
        await repo.create_delivery(
            session, ExecutionDelivery(execution_attempt_id=attempt.id, delivery_number=1, cause="recovery")
        )
    run.state, run.pause_reason, run.next_action_at = "awaiting_ci" if implemented else "dispatching", None, None
    run.revision += 1
    item.state, item.detail = "running", None
    await session.flush()
