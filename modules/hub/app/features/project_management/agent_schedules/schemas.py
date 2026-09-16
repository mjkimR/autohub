from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.ai_catalogs.schemas import AICatalogSessionRead
from app.features.scheduling.schedule_configs.schemas import _validate_cron_expression
from app_layer_base.base.schemas.mixin import TimestampSchemaMixin, UUIDSchemaMixin
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentScheduleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_catalog_id: UUID = Field(description="Catalog whose sessions this schedule starts; its kind picks the task")
    work_type: Literal["task", "report"] = Field(
        default="task",
        description="'task' work ends in a pull request adopted into the pipeline; a 'report' is stored from the session",
    )
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=20_000)
    starting_branch: str = Field(default="main", min_length=1, max_length=255)
    enabled: bool = True
    cron_expression: str | None = Field(default=None, max_length=100)
    interval_seconds: int | None = Field(default=None, ge=60, le=2_592_000)

    @model_validator(mode="after")
    def _one_trigger(self) -> "AgentScheduleWrite":
        if (self.cron_expression is None) == (self.interval_seconds is None):
            raise ValueError("Set exactly one of cron_expression or interval_seconds")
        if self.cron_expression is not None:
            _validate_cron_expression(self.cron_expression)
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Title cannot be blank")
        return self


class AgentScheduleRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    schedule_config_id: UUID
    ai_catalog_id: UUID
    work_type: str
    title: str
    prompt: str
    starting_branch: str
    enabled: bool
    cron_expression: str | None
    interval_seconds: int | None
    task_func: str = Field(default="", description="The scheduler task the owned schedule runs")
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    recent_sessions: list[AICatalogSessionRead] = Field(default_factory=list)


class AgentScheduleList(BaseModel):
    items: list[AgentScheduleRead]
