"""Bounded history retention. Domain work and provider cleanup are never deleted here."""

from datetime import datetime

from app.features.ai_catalogs.models import AICatalogSession
from app.features.configuration.system_configs.models import SystemConfig
from app.features.project_management.pipeline_runs.models import (
    FINAL_RUN_STATES,
    ExecutionAttempt,
    ExecutionDelivery,
    ExecutionReply,
    PipelineRun,
)
from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

HISTORY_CONFIG = "maintenance.history"


class HistoryRetentionRepository:
    async def lock_checkpoint(self, session: AsyncSession) -> SystemConfig:
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(
            insert(SystemConfig).values(name=HISTORY_CONFIG, data={}).on_conflict_do_nothing(index_elements=["name"])
        )
        return (
            await session.scalars(select(SystemConfig).where(SystemConfig.name == HISTORY_CONFIG).with_for_update())
        ).one()

    async def delete_runs(self, session: AsyncSession, *, before: datetime, now: datetime, limit: int = 200) -> int:
        ids = list(
            await session.scalars(
                select(PipelineRun.id)
                .where(
                    PipelineRun.state.in_(FINAL_RUN_STATES),
                    PipelineRun.updated_at < before,
                    or_(PipelineRun.lease_expires_at.is_(None), PipelineRun.lease_expires_at <= now),
                )
                .order_by(PipelineRun.updated_at, PipelineRun.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        if not ids:
            return 0
        # SET NULL alone would turn a completed Jules task back into pending PR adoption.
        # Retain the session/report and PR URL, but remember why its run link disappeared.
        await session.execute(
            update(AICatalogSession)
            .where(AICatalogSession.pipeline_run_id.in_(ids))
            .values(
                pipeline_run_id=None,
                pipeline_run_retired_at=now,
            )
        )
        attempts = select(ExecutionAttempt.id).where(ExecutionAttempt.pipeline_run_id.in_(ids))
        # Explicit deletion also works on SQLite configurations without FK enforcement.
        await session.execute(delete(ExecutionReply).where(ExecutionReply.execution_attempt_id.in_(attempts)))
        await session.execute(delete(ExecutionDelivery).where(ExecutionDelivery.execution_attempt_id.in_(attempts)))
        await session.execute(delete(ExecutionAttempt).where(ExecutionAttempt.pipeline_run_id.in_(ids)))
        await session.execute(delete(PipelineRun).where(PipelineRun.id.in_(ids)))
        return len(ids)
