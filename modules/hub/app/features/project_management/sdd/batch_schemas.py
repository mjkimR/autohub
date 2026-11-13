from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ControlBatch(BaseModel):
    request_id: UUID
    expected_revision: int = Field(ge=1)
    action: Literal["pause", "resume", "stop"]


class BatchRead(BaseModel):
    id: str
    project_id: str
    state: str
    revision: int
    exclusion: bool
    detail: str | None
    basis: dict
    evaluation: dict
    members: list[dict]
    retired: bool = True
