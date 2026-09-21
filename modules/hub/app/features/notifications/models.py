from datetime import datetime
from typing import ClassVar

from app.common.database import JSON_VARIANT
from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import Boolean, DateTime, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

NOTIFICATION_KIND_TELEGRAM = "telegram"


class NotificationChannel(Base, UUIDMixin, TimestampMixin):
    """A place the hub can reach its operator. Every enabled channel receives every notice."""

    __tablename__ = "notification_channels"
    __mapper_args__: ClassVar[dict] = {"eager_defaults": True}

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_level: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    # Non-secret destination settings; a Telegram channel keeps its ``chat_id`` here.
    config: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    # The channel's secret (a Telegram bot token), sealed like connector credentials.
    credentials_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credentials_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credential_key_version: Mapped[str] = mapped_column(String(255), nullable=False)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Why the most recent delivery failed; cleared by the next one that succeeds.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
