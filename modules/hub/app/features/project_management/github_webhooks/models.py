from datetime import datetime

from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class GitHubWebhookDelivery(Base, UUIDMixin, TimestampMixin):
    """Deduplication and processing audit without retaining GitHub payload content."""

    __tablename__ = "github_webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    repository: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    # What processing needs from the payload, so a delivery whose processing was lost can be replayed without
    # retaining the payload itself.
    pull_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    requested_catalog: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # "received" until handled, "retrying" while a sweep replays it, then "processed" or "failed".
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
