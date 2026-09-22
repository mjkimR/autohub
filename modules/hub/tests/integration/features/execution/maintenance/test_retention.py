from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog, AICatalogSession
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.configuration.system_configs.models import SystemConfig
from app.features.execution.tasks.domains.maintenance.history import HISTORY_CONFIG, HistoryRetentionRepository
from app.features.execution.tasks.domains.maintenance.repos import MaintenanceRepository
from app.features.execution.tasks.domains.maintenance.retention import HistoryRetentionUseCase
from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.pipeline_runs.models import (
    ExecutionAttempt,
    ExecutionDelivery,
    ExecutionReply,
    PipelineRun,
    PipelineRunState,
)
from app.features.scheduling.schedule_jobs.models import ScheduleJob, ScheduleJobStatus
from app.features.scheduling.schedule_jobs.repos import ScheduleJobRepository
from app_testing_base import utc_now
from sqlalchemy import select, update
from tests.integration.features.notifications.test_tick_housekeeping import make_run

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_expired_history_is_pruned_at_most_hourly(session):
    def job(name: str, status: str, days_old: int) -> ScheduleJob:
        return ScheduleJob(name=name, status=status, started_at=utc_now() - timedelta(days=days_old), payload={})

    def delivery(delivery_id: str, days_old: int) -> GitHubWebhookDelivery:
        return GitHubWebhookDelivery(
            delivery_id=delivery_id,
            event="push",
            payload_digest="0" * 64,
            status="processed",
            attempts=1,
            created_at=utc_now() - timedelta(days=days_old),
        )

    session.add_all(
        [
            job("old success", ScheduleJobStatus.SUCCESS, 4),
            job("recent success", ScheduleJobStatus.SUCCESS, 2),
            job("old failure", ScheduleJobStatus.FAILURE, 8),
            job("recent failure", ScheduleJobStatus.FAILURE, 6),
            delivery("ancient", 91),
            delivery("kept", 89),
        ]
    )
    await session.commit()

    await HistoryRetentionUseCase().execute()

    async def remaining() -> tuple[list[str], list[str]]:
        jobs = await session.scalars(
            select(ScheduleJob.name).where(ScheduleJob.schedule_config_id.is_(None)).order_by(ScheduleJob.name)
        )
        deliveries = await session.scalars(select(GitHubWebhookDelivery.delivery_id))
        return list(jobs), list(deliveries)

    assert await remaining() == (["recent failure", "recent success"], ["kept"])

    # Within the hour nothing is pruned again, including across independent maintenance invocations.
    session.add(job("old success again", ScheduleJobStatus.SUCCESS, 4))
    await session.commit()
    await HistoryRetentionUseCase().execute()
    assert "old success again" in (await remaining())[0]

    checkpoint = await session.scalar(
        select(SystemConfig).where(SystemConfig.name == HISTORY_CONFIG).execution_options(populate_existing=True)
    )
    checkpoint.data = {**checkpoint.data, "pruned_at": (utc_now() - timedelta(hours=2)).isoformat()}
    await session.commit()
    await HistoryRetentionUseCase().execute()
    assert "old success again" not in (await remaining())[0]


async def test_pending_and_retryable_jobs_survive_and_retention_uses_finish_time(session):
    now = utc_now()
    for name, status, retry_need, attempts, finish in (
        ("pending", "pending", False, 0, None),
        ("retryable", "failure", True, 1, now - timedelta(days=10)),
        ("exhausted", "failure", True, 3, now - timedelta(days=10)),
        ("recently finished", "success", False, 0, now),
        ("expired", "success", False, 0, now - timedelta(days=4)),
    ):
        session.add(
            ScheduleJob(
                name=name,
                status=status,
                started_at=now - timedelta(days=40),
                finished_at=finish,
                payload={},
                retry_need=retry_need,
                retry_attempts=attempts,
                retry_max=3,
            )
        )
    await session.commit()
    await HistoryRetentionUseCase().execute()
    assert set(await session.scalars(select(ScheduleJob.name))) == {"pending", "retryable", "recently finished"}


@pytest.mark.parametrize("state", list(PipelineRunState))
async def test_only_old_terminal_runs_expire(session, state):
    now = utc_now()
    run = await make_run(session, state=state)
    run_id = run.id
    await session.execute(
        update(PipelineRun).where(PipelineRun.id == run_id).values(updated_at=now - timedelta(days=31))
    )
    await session.commit()
    await HistoryRetentionUseCase().execute()
    remaining = await session.scalar(select(PipelineRun.id).where(PipelineRun.id == run_id))
    assert (remaining is None) == (state in ("completed", "failed", "canceled"))


async def test_recent_or_leased_runs_survive(session):
    now = utc_now()
    recent = await make_run(session, state="completed")
    leased = await make_run(session, state="failed")
    ids = {recent.id, leased.id}
    await session.execute(
        update(PipelineRun)
        .where(PipelineRun.id == leased.id)
        .values(updated_at=now - timedelta(days=31), lease_expires_at=now + timedelta(minutes=5))
    )
    await session.commit()
    await HistoryRetentionUseCase().execute()
    assert set(await session.scalars(select(PipelineRun.id))) == ids


async def test_expired_runs_remove_attempt_history_but_keep_sessions_without_readoption(session):
    now = utc_now()
    run = await make_run(session, state="completed")
    await session.execute(
        update(AICatalog).where(AICatalog.id == run.ai_catalog_id).values(kind="jules", adapter="jules-api")
    )
    await session.execute(
        update(PipelineRun).where(PipelineRun.id == run.id).values(updated_at=now - timedelta(days=31))
    )
    attempt = ExecutionAttempt(
        pipeline_run_id=run.id,
        attempt_number=1,
        kind="implementation",
        state="completed",
        request_snapshot={},
        request_digest="0" * 64,
        idempotency_key=uuid4(),
    )
    session.add(attempt)
    await session.flush()
    session.add_all(
        [
            ExecutionDelivery(execution_attempt_id=attempt.id, delivery_number=1),
            ExecutionReply(execution_attempt_id=attempt.id, external_id="reply", author="agent", replied_at=now),
        ]
    )
    provider_session = AICatalogSession(
        ai_catalog_id=run.ai_catalog_id,
        title="Finished task",
        state="completed",
        work_type="task",
        pipeline_run_id=run.id,
        pull_request_url=run.pull_url,
        result_summary="Keep the result",
    )
    session.add(provider_session)
    await session.commit()
    catalog_id = run.ai_catalog_id
    await HistoryRetentionUseCase().execute()
    await session.refresh(provider_session)
    assert provider_session.pipeline_run_id is None and provider_session.pipeline_run_retired_at is not None
    assert provider_session.result_summary == "Keep the result" and provider_session.pull_request_url == run.pull_url
    assert provider_session.failure_detail is None
    for model in (PipelineRun, ExecutionAttempt, ExecutionDelivery, ExecutionReply):
        assert list(await session.scalars(select(model.id))) == []
    assert await AICatalogRepository().list_sessions_awaiting_adoption(session, catalog_id) == []
    assert await MaintenanceRepository().pending_catalogs(session) == []


async def test_failed_pruning_rolls_back_deletion_and_can_retry_immediately(session, monkeypatch):
    run = await make_run(session, state="completed")
    run_id = run.id
    await session.execute(
        update(PipelineRun).where(PipelineRun.id == run_id).values(updated_at=utc_now() - timedelta(days=31))
    )
    await session.commit()
    with monkeypatch.context() as patch:
        patch.setattr(ScheduleJobRepository, "delete_history", AsyncMock(side_effect=RuntimeError("delete failed")))
        with pytest.raises(RuntimeError, match="delete failed"):
            await HistoryRetentionUseCase().execute()
    assert await session.scalar(select(PipelineRun.id).where(PipelineRun.id == run_id)) == run_id
    assert await session.scalar(select(SystemConfig).where(SystemConfig.name == HISTORY_CONFIG)) is None
    await session.commit()
    await HistoryRetentionUseCase().execute()
    assert await session.scalar(select(PipelineRun.id).where(PipelineRun.id == run_id)) is None


async def test_deletions_are_bounded(session):
    now = utc_now()
    for _ in range(3):
        run = await make_run(session, state="completed")
        await session.execute(
            update(PipelineRun).where(PipelineRun.id == run.id).values(updated_at=now - timedelta(days=31))
        )
        session.add(ScheduleJob(name="old", status="success", started_at=now - timedelta(days=4), payload={}))
    await session.flush()
    assert (
        await HistoryRetentionRepository().delete_runs(session, before=now - timedelta(days=30), now=now, limit=2) == 2
    )
    assert (
        await ScheduleJobRepository().delete_history(
            session, succeeded_before=now - timedelta(days=3), failed_before=now - timedelta(days=7), limit=2
        )
        == 2
    )
    assert len(list(await session.scalars(select(PipelineRun.id)))) == 1
    assert len(list(await session.scalars(select(ScheduleJob.id)))) == 1


async def test_concurrent_postgres_maintenance_prunes_only_once(session, monkeypatch):
    import asyncio

    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("Concurrent maintenance uses independent PostgreSQL transactions")
    await session.commit()
    delete_runs = AsyncMock(return_value=0)
    monkeypatch.setattr(HistoryRetentionRepository, "delete_runs", delete_runs)
    await asyncio.gather(*(HistoryRetentionUseCase().execute() for _ in range(3)))
    assert delete_runs.await_count == 1
