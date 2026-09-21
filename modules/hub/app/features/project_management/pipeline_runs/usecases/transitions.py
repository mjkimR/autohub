from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.features.project_management.pipeline_runs.models import (
    ExecutionAttemptState,
    PipelineRun,
    PipelineRunState,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    PipelineRunRead,
)
from sqlalchemy.ext.asyncio import AsyncSession

# Marks the synthetic attempt of a pull request implemented outside the pipeline; nothing was sent for it.
EXTERNAL_IMPLEMENTATION_STATUS = "implemented-externally"
ACTIVE_RUN_CONFLICT = "This pull request already has an active pipeline run"
PROJECT_CHANGED_BLOCK_REASON = (
    "Project changed after this pipeline run was enrolled; resume to continue with the new settings, "
    "or cancel it and enroll the pull request again if its repository or GitHub connection changed"
)
IN_FLIGHT_RESUME_WARNING = (
    " The agent may still be working on the previous request; resuming now can start duplicate work on the same branch."
)
GITHUB_BINDING_CHANGED_CONFLICT = (
    "Project repository or GitHub connection changed after this pipeline run was enrolled; "
    "cancel it and enroll the pull request again"
)


# All transitions below use the caller's session and retain its lock/transaction scope.


def as_utc(value: datetime) -> datetime:
    # SQLite returns naive values for DateTime(timezone=True); persisted times are UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def wait_on_github(run: PipelineRun, reason: str, now: datetime, delay: timedelta) -> None:
    """Keep an in-flight run where it is and look again after ``delay``.

    The run is not paused: a resume replays the agent's request, and nothing here is the agent's to redo. The
    reason is announced once, because only a changed reason moves the revision.
    """
    run.next_action_at = now + delay
    if run.pause_reason != reason:
        run.pause_reason = reason
        run.revision += 1


async def finish_closed_pull(
    repo: PipelineRunRepository, session: AsyncSession, run: PipelineRun, pr: dict, now: datetime
) -> None:
    merged = pr.get("merged") is True
    run.state = PipelineRunState.COMPLETED if merged else PipelineRunState.CANCELED
    run.pause_reason = None if merged else "Pull request was closed without a confirmed merge"
    run.next_action_at = None
    run.revision += 1
    attempt = await repo.active_attempt(session, run.id)
    if attempt is not None:
        attempt.state = ExecutionAttemptState.COMPLETED if merged else ExecutionAttemptState.FAILED
        attempt.finished_at = now
        attempt.failure_code = None if merged else "PR_CLOSED"
        attempt.failure_detail = run.pause_reason
    await session.flush()


async def block_for_project_change(
    repo: PipelineRunRepository, session: AsyncSession, run: PipelineRun, now: datetime
) -> PipelineRunRead:
    """A run pinned to an outdated project can never progress: release its catalog capacity and surface it."""
    attempt = await repo.active_attempt(session, run.id)
    # A delivered or uncertain delivery may still be running at the agent; warn before a resume duplicates it.
    in_flight = run.state == PipelineRunState.IMPLEMENTING or (
        attempt is not None and attempt.state == ExecutionAttemptState.DISPATCHING
    )
    reason = PROJECT_CHANGED_BLOCK_REASON + (IN_FLIGHT_RESUME_WARNING if in_flight else "")
    run.state = PipelineRunState.BLOCKED
    run.pause_reason = reason
    run.next_action_at = None
    run.revision += 1
    if attempt is not None:
        attempt.state = ExecutionAttemptState.FAILED
        attempt.finished_at = now
        attempt.failure_code = "PROJECT_CHANGED"
        attempt.failure_detail = reason
    await session.flush()
    return PipelineRunRead.model_validate(run)
