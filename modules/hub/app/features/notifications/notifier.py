import logging
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from app.features.notifications.services import NotificationChannelService
from app.features.notifications.telegram import TelegramError, create_telegram_client, send_telegram_message
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Delivery:
    channel_id: UUID
    channel_name: str
    error: str | None


class Notifier:
    """Sends one notice to the operator's channels and records how each delivery went.

    Sending never raises: a notice is a side effect of work that must not fail because of it.
    """

    def __init__(self, channels: Annotated[NotificationChannelService, Depends()]) -> None:
        self.channels = channels

    async def send(self, text: str, *, channel_id: UUID | None = None) -> list[Delivery]:
        """Deliver to every enabled channel, or to the one named channel even when it is disabled (a test)."""
        try:
            return await self._send(text, channel_id)
        except Exception:
            logger.exception("Sending a notification failed")
            return []

    async def _send(self, text: str, channel_id: UUID | None) -> list[Delivery]:
        async with AsyncTransaction() as session:
            rows = await self.channels.repo.list(session, enabled_only=channel_id is None)
            targets: list[tuple[UUID, str, str, str | None]] = []
            for row in rows:
                if channel_id is not None and row.id != channel_id:
                    continue
                chat_id = (row.config or {}).get("chat_id")
                try:
                    token = await self.channels.bot_token(row)
                except ValueError:
                    token = ""
                targets.append((row.id, row.name, token, str(chat_id) if chat_id else None))

        deliveries: list[Delivery] = []
        if targets:
            async with create_telegram_client() as client:
                for target_id, name, token, chat_id in targets:
                    error: str | None = None
                    if not token or not chat_id:
                        error = "The channel's bot token or chat id is missing or cannot be decrypted"
                    else:
                        try:
                            await send_telegram_message(client, token, chat_id, text)
                        except TelegramError as exc:
                            error = str(exc)
                    if error is not None:
                        logger.warning("Notification through channel %s failed: %s", name, error)
                    deliveries.append(Delivery(target_id, name, error))

        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            for delivery in deliveries:
                row = await self.channels.repo.get(session, delivery.channel_id, lock=True)
                if row is None:
                    continue
                row.last_error = delivery.error
                if delivery.error is None:
                    row.last_sent_at = now
        return deliveries
