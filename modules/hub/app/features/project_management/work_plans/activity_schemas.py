from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlanComment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    body: str = Field(min_length=1, max_length=8000)


class PlanActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: Literal["comment", "created", "updated", "control", "completed"]
    actor: str
    revision: int
    body: str
    changes: dict[str, Any]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PlanActivityList(BaseModel):
    items: list[PlanActivityRead]
    total_count: int
