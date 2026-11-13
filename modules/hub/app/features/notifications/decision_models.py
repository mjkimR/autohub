from datetime import datetime
from uuid import UUID

from app.common.database import JSON_VARIANT
from app.common.models import TimestampMixin
from app_layer_base.base.models.mixin import Base, UUIDMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class DecisionSubscription(Base, TimestampMixin):
    __tablename__ = "decision_subscriptions"
    channel_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification_channels.id", ondelete="CASCADE"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)
    scan_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scan_key: Mapped[str | None] = mapped_column(String(255))
    digest_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DecisionNotice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decision_notices"
    __table_args__ = (
        UniqueConstraint(
            "channel_id", "destination_generation", "decision_key", "fingerprint", name="uq_decision_notice_generation"
        ),
    )
    channel_id: Mapped[UUID] = mapped_column(ForeignKey("notification_channels.id", ondelete="CASCADE"), index=True)
    destination_generation: Mapped[int] = mapped_column(Integer)
    decision_key: Mapped[str] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20), default="pending")
    last_attempt_id: Mapped[UUID | None] = mapped_column()
    observed: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)


class DecisionNoticeAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decision_notice_attempts"
    channel_id: Mapped[UUID] = mapped_column(ForeignKey("notification_channels.id", ondelete="CASCADE"), index=True)
    destination_generation: Mapped[int] = mapped_column(Integer)
    notice_ids: Mapped[list] = mapped_column(JSON_VARIANT)
    message: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="sending")
    token: Mapped[UUID] = mapped_column()
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detail: Mapped[str | None] = mapped_column(String(100))


class DecisionNoticeRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decision_notice_requests"
    __table_args__ = (UniqueConstraint("channel_id", "operation", "request_id", name="uq_decision_notice_request"),)
    channel_id: Mapped[UUID] = mapped_column(ForeignKey("notification_channels.id", ondelete="CASCADE"))
    operation: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[UUID] = mapped_column()
    actor: Mapped[str] = mapped_column(String(255))
    digest: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON_VARIANT)


class DecisionNoticeQueue(Base):
    __tablename__ = "decision_notice_queue"
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    cursor: Mapped[str] = mapped_column(String(36), default="")
