from datetime import datetime

from app.features.scheduling.schedule_jobs.models import ScheduleJob, ScheduleJobStatus
from app.features.scheduling.schedule_jobs.schemas import ScheduleJobCreate, ScheduleJobPatch, ScheduleJobPut
from app_layer_base.base.repos.base import BaseRepository
from sqlalchemy import and_, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession


class ScheduleJobRepository(BaseRepository[ScheduleJob, ScheduleJobCreate, ScheduleJobPut, ScheduleJobPatch]):
    model = ScheduleJob

    async def delete_history(
        self, session: AsyncSession, *, succeeded_before: datetime, others_before: datetime
    ) -> None:
        """Drop old job rows. A success is one of thousands alike; anything else is kept longer for debugging."""
        await session.execute(
            delete(ScheduleJob).where(
                or_(
                    and_(ScheduleJob.status == ScheduleJobStatus.SUCCESS, ScheduleJob.started_at < succeeded_before),
                    and_(ScheduleJob.status != ScheduleJobStatus.SUCCESS, ScheduleJob.started_at < others_before),
                )
            )
        )
