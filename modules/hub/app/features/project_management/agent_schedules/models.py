from uuid import UUID

from app_layer_base.base.models.mixin import Base, TimestampMixin, UUIDMixin
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class ProjectAgentSchedule(Base, UUIDMixin, TimestampMixin):
    """A project's recurring agent session, owning the generic schedule that runs it.

    The row holds what an operator decides (catalog, work type, prompt, trigger). The owned ``ScheduleConfig`` is
    derived from it and the project on every save; nobody edits that config directly.
    """

    __tablename__ = "project_agent_schedules"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    schedule_config_id: Mapped[UUID] = mapped_column(
        ForeignKey("schedule_configs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    ai_catalog_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_catalogs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    work_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    starting_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
