from datetime import datetime
from uuid import UUID, uuid4

from app.common.database import JSON_VARIANT
from app_layer_base.base.models.mixin import Base, TimestampMixin
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column


class FlowIdMixin:
    # CHAR(32) on SQLite avoids the NUMERIC affinity of a literal UUID column.
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)


class FlowEnvironment(Base, TimestampMixin):
    __tablename__ = "sdk_flow_environments"
    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    environment: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_machine_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    active_release_id: Mapped[str | None] = mapped_column(String(128))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FlowRelease(Base, FlowIdMixin, TimestampMixin):
    __tablename__ = "sdk_flow_releases"
    __table_args__ = (
        UniqueConstraint("provider", "environment", "release_id", name="uq_sdk_flow_release_identity"),
        ForeignKeyConstraint(
            ["provider", "environment"], ["sdk_flow_environments.provider", "sdk_flow_environments.environment"]
        ),
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False)
    release_id: Mapped[str] = mapped_column(String(128), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    definition: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    bindings: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)


class FlowRun(Base, FlowIdMixin, TimestampMixin):
    __tablename__ = "sdk_flow_runs"
    __table_args__ = (
        UniqueConstraint("provider", "environment", "request_key", name="uq_sdk_flow_run_request"),
        Index("ix_sdk_flow_ready", "status", "next_action_at"),
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(64), nullable=False)
    release_pk: Mapped[UUID] = mapped_column(ForeignKey("sdk_flow_releases.id"), nullable=False)
    request_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    task_key: Mapped[str] = mapped_column(String(256), nullable=False)
    task_version: Mapped[int] = mapped_column(Integer, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    error: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column(Uuid)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FlowStep(Base, FlowIdMixin, TimestampMixin):
    __tablename__ = "sdk_flow_steps"
    __table_args__ = (UniqueConstraint("run_id", "step_key", name="uq_sdk_flow_step_key"),)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False)
    step_key: Mapped[str] = mapped_column(String(128), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rework_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FlowAttempt(Base, FlowIdMixin, TimestampMixin):
    __tablename__ = "sdk_flow_attempts"
    __table_args__ = (UniqueConstraint("step_id", "number", name="uq_sdk_flow_attempt_number"),)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False)
    step_id: Mapped[UUID] = mapped_column(ForeignKey("sdk_flow_steps.id", ondelete="CASCADE"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="intent")
    inputs: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    output: Mapped[dict | None] = mapped_column(JSON_VARIANT)
    error: Mapped[str | None] = mapped_column(Text)


class FlowCommand(Base, FlowIdMixin, TimestampMixin):
    __tablename__ = "sdk_flow_commands"
    __table_args__ = (UniqueConstraint("run_id", "command_key", name="uq_sdk_flow_command_identity"),)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("sdk_flow_runs.id", ondelete="CASCADE"), nullable=False)
    command_key: Mapped[str] = mapped_column(String(128), nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    receipt: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)


class FlowPRLink(Base, TimestampMixin):
    __tablename__ = "sdk_flow_pr_links"
    pipeline_run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("pipeline_runs.id"), primary_key=True)
    flow_run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sdk_flow_runs.id"), nullable=False, unique=True)
    evidence: Mapped[dict] = mapped_column(JSON_VARIANT, nullable=False)
    delivery_attempt_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    canceled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_revision: Mapped[int | None] = mapped_column(Integer)
    approved_digest: Mapped[str | None] = mapped_column(String(64))
    approved_actor: Mapped[str | None] = mapped_column(String(128))
