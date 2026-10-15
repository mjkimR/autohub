"""Recover push evidence lost when project changes settled an implementation attempt."""

from app.features.project_management.pipeline_runs.models import ExecutionAttempt
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest
from sqlalchemy.ext.asyncio import AsyncSession


async def project_change_push(
    repo: PipelineRunRepository,
    session: AsyncSession,
    attempts: list[ExecutionAttempt],
    head_sha: str,
) -> bool:
    if not attempts:
        return False
    # Resume changes the marker and observed head, but preserves the work. Never borrow evidence
    # across a CI/conflict fix or an operator answer that changed the instructions.
    exclude = {"correlation_marker": True, "pull_request": {"head_sha"}}
    latest = ImplementationRequest.model_validate(attempts[-1].request_snapshot).model_dump(exclude=exclude)
    for attempt in reversed(attempts):
        request = ImplementationRequest.model_validate(attempt.request_snapshot)
        if request.model_dump(exclude=exclude) != latest:
            break
        if attempt.failure_code == "PROJECT_CHANGED" and request.pull_request.head_sha != head_sha:
            deliveries = await repo.list_deliveries(session, attempt.id)
            if any(delivery.posted_at is not None for delivery in deliveries):
                return True
        if attempt.failure_code not in (None, "PROJECT_CHANGED", "USER_RESUMED"):
            break
    return False
