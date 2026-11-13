"""Retained replacement relations, exact edge decisions and immutable command receipts."""

from uuid import UUID

from app.common.database import JSON_VARIANT
from app.common.models import TimestampMixin
from app_layer_base.base.models.mixin import Base, UUIDMixin
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column


class ReplacementEvidence(Base):
    __tablename__ = "work_replacement_evidence"
    item_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="RESTRICT"), primary_key=True)
    revision: Mapped[int] = mapped_column(default=0)


class ReplacementLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_replacement_links"
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "original_plan_id"], ["work_plans.project_id", "work_plans.id"]),
        ForeignKeyConstraint(["project_id", "replacement_plan_id"], ["work_plans.project_id", "work_plans.id"]),
        ForeignKeyConstraint(["original_plan_id", "original_item_id"], ["work_items.plan_id", "work_items.id"]),
        ForeignKeyConstraint(["replacement_plan_id", "replacement_item_id"], ["work_items.plan_id", "work_items.id"]),
        UniqueConstraint("replacement_item_id", name="uq_replacement_lifetime_endpoint"),
        Index(
            "uq_replacement_active_original",
            "original_item_id",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
    )
    project_id: Mapped[UUID] = mapped_column()
    original_plan_id: Mapped[UUID] = mapped_column()
    original_item_id: Mapped[UUID] = mapped_column(index=True)
    replacement_plan_id: Mapped[UUID] = mapped_column()
    replacement_item_id: Mapped[UUID] = mapped_column()
    active: Mapped[bool] = mapped_column(default=True)
    snapshot: Mapped[dict] = mapped_column(JSON_VARIANT)
    actor: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(String(500))


class ReplacementAcceptance(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_replacement_acceptances"
    __table_args__ = (
        ForeignKeyConstraint(["plan_id", "dependent_item_id"], ["work_items.plan_id", "work_items.id"]),
        ForeignKeyConstraint(["plan_id", "original_item_id"], ["work_items.plan_id", "work_items.id"]),
        Index(
            "uq_replacement_live_edge",
            "dependent_item_id",
            "original_item_id",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
    )
    link_id: Mapped[UUID] = mapped_column(ForeignKey("work_replacement_links.id", ondelete="RESTRICT"), index=True)
    plan_id: Mapped[UUID] = mapped_column()
    dependent_item_id: Mapped[UUID] = mapped_column()
    original_item_id: Mapped[UUID] = mapped_column()
    active: Mapped[bool] = mapped_column(default=True)
    consumed: Mapped[bool] = mapped_column(default=False)
    snapshot: Mapped[dict] = mapped_column(JSON_VARIANT)
    actor: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(String(500))


class ReplacementEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_replacement_events"
    link_id: Mapped[UUID] = mapped_column(ForeignKey("work_replacement_links.id", ondelete="RESTRICT"), index=True)
    acceptance_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("work_replacement_acceptances.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(String(500))
    revision: Mapped[int] = mapped_column()
    evidence: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)


class ReplacementReceipt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_replacement_receipts"
    __table_args__ = (UniqueConstraint("project_id", "operation", "request_id", name="uq_replacement_request"),)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    original_item_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="RESTRICT"))
    operation: Mapped[str] = mapped_column(String(30))
    request_id: Mapped[UUID] = mapped_column()
    digest: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON_VARIANT)
