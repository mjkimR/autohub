from datetime import datetime
from typing import Literal

from app_layer_base.base.schemas.mixin import TimestampSchemaMixin, UUIDSchemaMixin
from pydantic import BaseModel, ConfigDict, Field

NotificationKind = Literal["telegram"]


class NotificationChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    kind: NotificationKind = "telegram"
    enabled: bool = True
    chat_id: str = Field(min_length=1, max_length=255, description="Telegram chat the bot posts to")
    bot_token: str = Field(min_length=1, max_length=255, description="Telegram bot token from @BotFather")


class NotificationChannelPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    chat_id: str | None = Field(default=None, min_length=1, max_length=255)
    # Omitted keeps the stored token.
    bot_token: str | None = Field(default=None, min_length=1, max_length=255)


class NotificationChannelRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: str
    enabled: bool
    chat_id: str | None
    last_sent_at: datetime | None
    last_error: str | None


class NotificationChannelList(BaseModel):
    items: list[NotificationChannelRead]


class NotificationTestResult(BaseModel):
    delivered: bool
    detail: str | None = None
