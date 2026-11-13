"""Immutable selected intent and durable native-owner admission checkpoints."""

from uuid import UUID

from app.common.database import JSON_VARIANT
from app.common.models import TimestampMixin
from app_layer_base.base.models.mixin import Base, UUIDMixin
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column


class SddBatch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sdd_batches"
    __table_args__ = (
        UniqueConstraint("project_id", "request_id"),
        Index(
            "uq_sdd_batch_exclusion",
            "project_id",
            unique=True,
            sqlite_where=text("exclusion = true"),
            postgresql_where=text("exclusion = true"),
        ),
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(30), default="running")
    revision: Mapped[int] = mapped_column(default=1)
    exclusion: Mapped[bool] = mapped_column(default=True)
    basis: Mapped[dict] = mapped_column(JSON_VARIANT)
    evaluation: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)
    detail: Mapped[str | None] = mapped_column(String(2048))


class SddBatchMember(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sdd_batch_members"
    __table_args__ = (UniqueConstraint("batch_id", "position"), UniqueConstraint("batch_id", "anchor_id"))
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("sdd_batches.id", ondelete="RESTRICT"))
    position: Mapped[int] = mapped_column()
    anchor_id: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    initial: Mapped[dict] = mapped_column(JSON_VARIANT)
    phase: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(30), default="waiting")
    spec_anchor: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    outcome: Mapped[dict | None] = mapped_column(JSON_VARIANT)


class SddActivityClaim(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sdd_activity_claims"
    __table_args__ = (
        UniqueConstraint("project_id", "request_id"),
        Index(
            "uq_sdd_activity_claim_live",
            "project_id",
            "unit",
            "activity",
            unique=True,
            sqlite_where=text("settled = false"),
            postgresql_where=text("settled = false"),
        ),
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    member_id: Mapped[UUID | None] = mapped_column(ForeignKey("sdd_batch_members.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    actor: Mapped[str] = mapped_column(String(255))
    request_digest: Mapped[str] = mapped_column(String(64))
    unit: Mapped[str] = mapped_column(String(255))
    activity: Mapped[str] = mapped_column(String(10))
    settled: Mapped[bool] = mapped_column(default=False)
    checkpoint: Mapped[dict] = mapped_column(JSON_VARIANT)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="RESTRICT"))


class SddBatchControl(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sdd_batch_controls"
    __table_args__ = (UniqueConstraint("batch_id", "request_id"),)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("sdd_batches.id", ondelete="RESTRICT"))
    request_id: Mapped[UUID] = mapped_column()
    actor: Mapped[str] = mapped_column(String(255))
    request_digest: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(10))
