from datetime import datetime

from app.features.scheduling.schedule_jobs.models import ScheduleJob, ScheduleJobStatus
from app.features.scheduling.schedule_jobs.schemas import ScheduleJobCreate, ScheduleJobPatch, ScheduleJobPut
from app_layer_base.base.repos.base import BaseRepository
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class ScheduleJobRepository(BaseRepository[ScheduleJob, ScheduleJobCreate, ScheduleJobPut, ScheduleJobPatch]):
    model = ScheduleJob

    async def delete_history(
        self, session: AsyncSession, *, succeeded_before: datetime, failed_before: datetime, limit: int = 1000
    ) -> int:
        """Expire terminal jobs by finish time, preserving pending work and eligible retries.

        Legacy terminal records with no finish time use their last execution's start time.
        """
        ended_at = func.coalesce(ScheduleJob.finished_at, ScheduleJob.started_at)
        ids = list(
            await session.scalars(
                select(ScheduleJob.id)
                .where(
                    or_(ScheduleJob.retry_need.is_(False), ScheduleJob.retry_attempts >= ScheduleJob.retry_max),
                    or_(
                        and_(ScheduleJob.status == ScheduleJobStatus.SUCCESS, ended_at < succeeded_before),
                        and_(ScheduleJob.status == ScheduleJobStatus.FAILURE, ended_at < failed_before),
                    ),
                )
                .order_by(ended_at, ScheduleJob.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        if ids:
            await session.execute(delete(ScheduleJob).where(ScheduleJob.id.in_(ids)))
        return len(ids)
