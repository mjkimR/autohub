from bisect import bisect_right
from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from app.features.ai_catalogs.models import (
    SESSION_TERMINAL_STATES,
    SESSION_WORK_TYPE_TASK,
    AICatalog,
    AICatalogKind,
    AICatalogSession,
)
from app.features.configuration.system_configs.models import SystemConfig
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

QUEUE_CONFIG = "maintenance.queue"
MaintenanceGroup = Literal["tests", "catalogs"]


class MaintenanceRepository:
    async def next_item(self, session: AsyncSession, group: MaintenanceGroup, pending: Sequence[str]) -> str:
        """Rotate a sorted, nonempty pending list after the last attempted item.

        Commit the cursor before external work so cancellation or failure still gives the next item a turn.
        Only two cursors are retained, regardless of the number of pending items.
        """
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(
            insert(SystemConfig).values(name=QUEUE_CONFIG, data={}).on_conflict_do_nothing(index_elements=["name"])
        )
        checkpoint = (
            await session.scalars(select(SystemConfig).where(SystemConfig.name == QUEUE_CONFIG).with_for_update())
        ).one()
        data = checkpoint.data or {}
        previous = data.get(group)
        index = bisect_right(pending, previous) if isinstance(previous, str) else 0
        item = pending[index % len(pending)]
        checkpoint.data = {**data, group: item}
        return item

    async def pending_tests(self, session: AsyncSession) -> list[UUID]:
        # Include canceled/failed tests with unfinished cleanup even on disabled projects.
        return list(
            await session.scalars(
                select(ConnectionTest.id)
                .where(or_(ConnectionTest.status == ACTIVE, ConnectionTest.cleanup_status != "completed"))
                .order_by(ConnectionTest.updated_at, ConnectionTest.id)
            )
        )

    async def pending_catalogs(self, session: AsyncSession) -> list[str]:
        # Agent schedules may have been disabled/deleted. A completed task may still need adoption.
        pending = select(AICatalogSession.id).where(
            AICatalogSession.ai_catalog_id == AICatalog.id,
            or_(
                AICatalogSession.state.not_in(SESSION_TERMINAL_STATES),
                and_(
                    AICatalogSession.state == "completed",
                    AICatalogSession.work_type == SESSION_WORK_TYPE_TASK,
                    AICatalogSession.pull_request_url.is_not(None),
                    AICatalogSession.pipeline_run_id.is_(None),
                    AICatalogSession.pipeline_run_retired_at.is_(None),
                    AICatalogSession.failure_detail.is_(None),
                ),
            ),
        )
        return list(
            await session.scalars(
                select(AICatalog.key)
                .where(AICatalog.kind == AICatalogKind.JULES, pending.exists())
                .order_by(AICatalog.id)
            )
        )
