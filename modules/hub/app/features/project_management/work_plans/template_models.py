from uuid import UUID

from app.common.database import JSON_VARIANT
from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class WorkPlanTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_plan_templates"
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(default=1)
    deleted: Mapped[bool] = mapped_column(default=False)
    schema_version: Mapped[int] = mapped_column(default=1)
    definition: Mapped[dict] = mapped_column(JSON_VARIANT)
    created_actor: Mapped[str] = mapped_column(String(255))
    updated_actor: Mapped[str] = mapped_column(String(255))


class TemplateRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_template_requests"
    __table_args__ = (UniqueConstraint("project_id", "operation", "request_id", name="uq_work_template_request"),)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    operation: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[UUID] = mapped_column()
    actor: Mapped[str] = mapped_column(String(255))
    digest: Mapped[str] = mapped_column(String(64))
    template_id: Mapped[UUID] = mapped_column()
    plan_id: Mapped[UUID | None] = mapped_column()
    result: Mapped[dict] = mapped_column(JSON_VARIANT)
