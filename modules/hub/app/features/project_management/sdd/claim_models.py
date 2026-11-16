"""Durable repository activity publication ownership."""

from uuid import UUID

from app.common.database import JSON_VARIANT
from app.common.models import TimestampMixin
from app_layer_base.base.models.mixin import Base, UUIDMixin
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column


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
    request_id: Mapped[UUID] = mapped_column()
    actor: Mapped[str] = mapped_column(String(255))
    request_digest: Mapped[str] = mapped_column(String(64))
    unit: Mapped[str] = mapped_column(String(255))
    activity: Mapped[str] = mapped_column(String(10))
    settled: Mapped[bool] = mapped_column(default=False)
    checkpoint: Mapped[dict] = mapped_column(JSON_VARIANT)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("pipeline_runs.id", ondelete="RESTRICT"))
