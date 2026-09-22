"""The installation-owned maintenance schedule; independent of projects and agent schedules."""

from uuid import UUID

from app.features.scheduling.schedule_configs.models import ScheduleConfig
from sqlalchemy import or_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

MAINTENANCE_ID = UUID("cd9c8a55-70df-4b91-a988-2b3e756c0110")
MAINTENANCE_TASK = "system.maintain"
MAINTENANCE_NAME = "System maintenance"
MAINTENANCE_INTERVAL = 60


async def ensure_maintenance_schedule(session: AsyncSession) -> None:
    """Seed once, repair missing/disabled configuration, and preserve a healthy schedule's due time.

    The stable primary key arbitrates concurrent startup/tick repair. No external I/O is done here.
    """
    insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
    fields = {
        "name": MAINTENANCE_NAME,
        "description": "Progresses connection tests, cleans up test resources, and collects Jules session results",
        "task_func": MAINTENANCE_TASK,
        "interval_seconds": MAINTENANCE_INTERVAL,
        "cron_expression": None,
        "payload": {},
        "enabled": True,
        "start_at": None,
        "end_at": None,
    }
    # Concurrent inserts can collide on either the primary key or the partial task index.
    await session.execute(insert(ScheduleConfig).values(id=MAINTENANCE_ID, **fields).on_conflict_do_nothing())
    await session.execute(
        update(ScheduleConfig)
        .where(
            ScheduleConfig.id == MAINTENANCE_ID,
            or_(
                ScheduleConfig.enabled.is_(False),
                ScheduleConfig.task_func != MAINTENANCE_TASK,
                ScheduleConfig.interval_seconds.is_(None),
                ScheduleConfig.interval_seconds != MAINTENANCE_INTERVAL,
                ScheduleConfig.cron_expression.is_not(None),
                ScheduleConfig.start_at.is_not(None),
                ScheduleConfig.end_at.is_not(None),
            ),
        )
        .values(**fields, next_run_at=None)
    )
