from datetime import datetime
from uuid import UUID

from app.common.database import JSON_VARIANT
from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


class WorkPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_plans"
    __table_args__ = (UniqueConstraint("project_id", "id"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    repository: Mapped[str] = mapped_column(String(255))
    connector_id: Mapped[UUID] = mapped_column(ForeignKey("connectors.id", ondelete="RESTRICT"))
    base_branch: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(30), default="active")
    revision: Mapped[int] = mapped_column(default=1)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_items"
    __table_args__ = (UniqueConstraint("plan_id", "key"), UniqueConstraint("plan_id", "id"))

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("work_plans.id", ondelete="RESTRICT"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    acceptance: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(30), default="waiting", index=True)
    detail: Mapped[str | None] = mapped_column(Text)
    ai_catalog_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_catalogs.id", ondelete="RESTRICT"))
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"), unique=True
    )
    execution_id: Mapped[UUID | None] = mapped_column()
    pipeline_run_retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    branch: Mapped[str | None] = mapped_column(String(255))
    base_sha: Mapped[str | None] = mapped_column(String(64))
    pull_number: Mapped[int | None] = mapped_column()
    pull_url: Mapped[str | None] = mapped_column(String(2048))
    merge_sha: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlanDependency(Base):
    __tablename__ = "work_plan_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(["project_id", "plan_id"], ["work_plans.project_id", "work_plans.id"]),
        ForeignKeyConstraint(["project_id", "depends_on_id"], ["work_plans.project_id", "work_plans.id"]),
        CheckConstraint("plan_id <> depends_on_id", name="ck_work_plan_no_self_dependency"),
    )
    project_id: Mapped[UUID] = mapped_column()
    plan_id: Mapped[UUID] = mapped_column(primary_key=True)
    depends_on_id: Mapped[UUID] = mapped_column(primary_key=True)


class ItemDependency(Base):
    __tablename__ = "work_item_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(["plan_id", "item_id"], ["work_items.plan_id", "work_items.id"]),
        ForeignKeyConstraint(["plan_id", "depends_on_id"], ["work_items.plan_id", "work_items.id"]),
        CheckConstraint("item_id <> depends_on_id", name="ck_work_item_no_self_dependency"),
    )
    plan_id: Mapped[UUID] = mapped_column()
    item_id: Mapped[UUID] = mapped_column(primary_key=True)
    depends_on_id: Mapped[UUID] = mapped_column(primary_key=True)


class WorkIssueMirror(Base, UUIDMixin, TimestampMixin):
    """Outbound-only snapshot; remote content is never execution input."""

    __tablename__ = "work_issue_mirrors"
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("work_plans.id", ondelete="RESTRICT"), index=True)
    entity_id: Mapped[UUID] = mapped_column(unique=True)
    desired: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)
    digest: Mapped[str] = mapped_column(String(64))
    synced_digest: Mapped[str | None] = mapped_column(String(64))
    issue_number: Mapped[int | None] = mapped_column()
    issue_id: Mapped[int | None] = mapped_column(BigInteger)
    issue_url: Mapped[str | None] = mapped_column(String(2048))
    create_attempted: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column()
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
