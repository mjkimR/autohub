from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .schemas import MilestonePreviewRequest, StartActivityRequest


class BatchSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^PROP-[a-z0-9][a-z0-9_-]*$", max_length=64)
    path: str = Field(max_length=1024)
    activity: Literal["plan", "dev"]
    planning_effort: Literal["low", "medium", "high"] | None = None
    dev_effort: Literal["low", "medium", "high"] | None = None
    planning_catalog: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    dev_catalog: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")


class CreateBatch(MilestonePreviewRequest):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    expected_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    through_development: Literal[True]
    members: list[BatchSelection] = Field(min_length=1, max_length=50)


class ControlBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


def activity_request(member: dict, phase: str, request_id, base: str) -> StartActivityRequest:
    name = "planning" if phase == "plan" else "dev"
    return StartActivityRequest(
        request_id=request_id,
        base_branch=base,
        activity_effort=member.get(f"{name}_effort"),
        catalog=member.get(f"{name}_catalog"),
    )
