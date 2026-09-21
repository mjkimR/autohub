from typing import Annotated, cast
from uuid import UUID

from app.features.notifications.models import NotificationChannel
from app.features.notifications.notifier import Notifier
from app.features.notifications.schemas import (
    NotificationChannelCreate,
    NotificationChannelList,
    NotificationChannelPatch,
    NotificationChannelRead,
    NotificationLevel,
    NotificationTestResult,
)
from app.features.notifications.services import NotificationChannelService
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


def _read(channel: NotificationChannel) -> NotificationChannelRead:
    chat_id = (channel.config or {}).get("chat_id")
    return NotificationChannelRead(
        id=channel.id,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        name=channel.name,
        kind=channel.kind,
        enabled=channel.enabled,
        min_level=cast(NotificationLevel, channel.min_level),
        chat_id=str(chat_id) if chat_id else None,
        last_sent_at=channel.last_sent_at,
        last_error=channel.last_error,
    )


class NotificationChannelUseCase:
    def __init__(
        self,
        service: Annotated[NotificationChannelService, Depends()],
        notifier: Annotated[Notifier, Depends()],
    ) -> None:
        self.service = service
        self.notifier = notifier

    async def list(self) -> NotificationChannelList:
        async with AsyncTransaction() as session:
            return NotificationChannelList(items=[_read(row) for row in await self.service.list(session)])

    async def create(self, data: NotificationChannelCreate) -> NotificationChannelRead:
        async with AsyncTransaction() as session:
            return _read(await self.service.create(session, data))

    async def patch(self, channel_id: UUID, data: NotificationChannelPatch) -> NotificationChannelRead:
        async with AsyncTransaction() as session:
            return _read(await self.service.patch(session, channel_id, data))

    async def delete(self, channel_id: UUID) -> None:
        async with AsyncTransaction() as session:
            await self.service.delete(session, channel_id)

    async def send_test(self, channel_id: UUID) -> NotificationTestResult:
        deliveries = await self.notifier.send(
            "Auto Hub test notification. This channel will receive notices about runs that need you.",
            channel_id=channel_id,
        )
        if not deliveries:
            raise ProjectError(404, "Notification channel not found")
        return NotificationTestResult(delivered=deliveries[0].error is None, detail=deliveries[0].error)
