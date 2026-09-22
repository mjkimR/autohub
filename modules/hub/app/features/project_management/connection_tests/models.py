from datetime import datetime
from uuid import UUID

from app.common.database import JSON_VARIANT
from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

TEST_BRANCH_PREFIX = "autohub-connection-test/"
TEST_TASK = "pipeline.connection_test"
ACTIVE = "running"


class ConnectionTest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "connection_tests"
    __table_args__ = (
        Index("ix_connection_tests_project_created", "project_id", "created_at"),
        Index(
            "uq_connection_tests_active_project",
            "project_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
            sqlite_where=text("status = 'running'"),
        ),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    project_revision: Mapped[int] = mapped_column()
    repository: Mapped[str] = mapped_column(String(255))
    connector_id: Mapped[UUID] = mapped_column()
    ai_catalog_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_catalogs.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    catalog_snapshot: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)
    verification: Mapped[dict] = mapped_column(JSON_VARIANT)
    status: Mapped[str] = mapped_column(String(30), default=ACTIVE)
    phase: Mapped[str] = mapped_column(String(30), default="preparing")
    cleanup_status: Mapped[str] = mapped_column(String(30), default="pending")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
