from datetime import datetime
from uuid import UUID

from app.common.database import JSON_VARIANT
from app.common.models import TimestampMixin
from app_layer_base.base.models.mixin import Base, UUIDMixin
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column


class WorkPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_plans"
    __table_args__ = (
        UniqueConstraint("project_id", "id"),
        UniqueConstraint("project_id", "registration_request_id", name="uq_work_plan_registration"),
        Index("ix_work_plans_project_group", "project_id", "group_key"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    registration_request_id: Mapped[UUID | None] = mapped_column()
    registration_digest: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    group_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    repository: Mapped[str] = mapped_column(String(255))
    connector_id: Mapped[UUID] = mapped_column(ForeignKey("connectors.id", ondelete="RESTRICT"))
    base_branch: Mapped[str] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(30), default="active")
    revision: Mapped[int] = mapped_column(default=1)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    # An existing activity branch the operator attached explicitly; otherwise the item starts dev-<key>.
    attach_branch: Mapped[str | None] = mapped_column(String(64))
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


class WorkPlanActivity(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_plan_activities"
    __table_args__ = (UniqueConstraint("plan_id", "request_id", name="uq_work_plan_comment_request"),)

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("work_plans.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID | None] = mapped_column()
    kind: Mapped[str] = mapped_column(String(30))
    actor: Mapped[str] = mapped_column(String(255))
    revision: Mapped[int] = mapped_column()
    body: Mapped[str] = mapped_column(Text, default="")
    changes: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)


class WorkItemRecovery(Base, UUIDMixin, TimestampMixin):
    """Immutable command and prior outcome; mutable progress is also recorded as events."""

    __tablename__ = "work_item_recoveries"
    __table_args__ = (
        UniqueConstraint("project_id", "request_id", name="uq_work_item_recovery_request"),
        Index(
            "uq_work_item_pending_recovery",
            "item_id",
            unique=True,
            postgresql_where=text("state IN ('accepted', 'reconciling', 'awaiting-admission')"),
            sqlite_where=text("state IN ('accepted', 'reconciling', 'awaiting-admission')"),
        ),
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"))
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("work_plans.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="RESTRICT"), index=True)
    request_id: Mapped[UUID] = mapped_column()
    request_digest: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(String(500))
    command: Mapped[dict] = mapped_column(JSON_VARIANT)
    prior_outcome: Mapped[dict] = mapped_column(JSON_VARIANT)
    accepted_revision: Mapped[int] = mapped_column()
    accepted_run_revision: Mapped[int | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(30), default="accepted")
    detail: Mapped[str] = mapped_column(Text, default="Accepted; checking original execution")
    lease_generation: Mapped[int] = mapped_column(default=0)


class WorkItemRecoveryEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_item_recovery_events"
    __table_args__ = (UniqueConstraint("recovery_id", "sequence", name="uq_work_item_recovery_event_sequence"),)
    sequence: Mapped[int] = mapped_column()
    recovery_id: Mapped[UUID] = mapped_column(ForeignKey("work_item_recoveries.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)


# Register additive replacement metadata alongside the owning Work Plan models.
from app.features.project_management.work_plans.replacement_models import (  # noqa: E402,F401
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementEvidence,
    ReplacementLink,
    ReplacementReceipt,
)

# Register additive template metadata alongside the owner models.
from app.features.project_management.work_plans.template_models import (  # noqa: E402,F401
    TemplateRequest,
    WorkPlanTemplate,
)
