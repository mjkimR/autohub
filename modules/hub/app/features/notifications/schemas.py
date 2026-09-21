from datetime import datetime
from typing import Literal

from app_layer_base.base.schemas.mixin import TimestampSchemaMixin, UUIDSchemaMixin
from pydantic import BaseModel, ConfigDict, Field

NotificationKind = Literal["telegram"]
NotificationLevel = Literal["debug", "info", "warning", "error", "critical"]

LEVEL_ORDER: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
}


def is_level_enabled(channel_level: str, notice_level: str) -> bool:
    channel_rank = LEVEL_ORDER.get(channel_level.lower(), 20)
    notice_rank = LEVEL_ORDER.get(notice_level.lower(), 20)
    return notice_rank >= channel_rank


class NotificationChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: NotificationKind = "telegram"
    enabled: bool = True
    min_level: NotificationLevel = "info"
    chat_id: str = Field(min_length=1, max_length=255, description="Telegram chat the bot posts to")
    bot_token: str = Field(min_length=1, max_length=255, description="Telegram bot token from @BotFather")


class NotificationChannelPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    min_level: NotificationLevel | None = None
    chat_id: str | None = Field(default=None, min_length=1, max_length=255)
    # Omitted keeps the stored token.
    bot_token: str | None = Field(default=None, min_length=1, max_length=255)


class NotificationChannelRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: str
    enabled: bool
    min_level: NotificationLevel
    chat_id: str | None
    last_sent_at: datetime | None
    last_error: str | None


class NotificationChannelList(BaseModel):
    items: list[NotificationChannelRead]


class NotificationTestResult(BaseModel):
    delivered: bool
    detail: str | None = None
