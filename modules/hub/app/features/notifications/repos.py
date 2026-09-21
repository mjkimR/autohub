from collections.abc import Sequence
from uuid import UUID

from app.features.notifications.models import NotificationChannel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class NotificationChannelRepository:
    async def list(self, session: AsyncSession, *, enabled_only: bool = False) -> Sequence[NotificationChannel]:
        query = select(NotificationChannel).order_by(NotificationChannel.name)
        if enabled_only:
            query = query.where(NotificationChannel.enabled.is_(True))
        return (await session.scalars(query)).all()

    async def get(self, session: AsyncSession, channel_id: UUID, *, lock: bool = False) -> NotificationChannel | None:
        return await session.get(NotificationChannel, channel_id, with_for_update=lock)

    async def get_by_name(self, session: AsyncSession, name: str) -> NotificationChannel | None:
        return await session.scalar(select(NotificationChannel).where(NotificationChannel.name == name))
