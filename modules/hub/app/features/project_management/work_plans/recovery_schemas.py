from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkItemRecover(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    expected_revision: int = Field(ge=1)
    expected_run_revision: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=500)


class RecoveryEligibility(BaseModel):
    eligible: bool
    reason: str
    next_action: str
    run_revision: int | None = None
    pending_state: str | None = None
    pending_detail: str | None = None


class RecoveryEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    detail: str
    evidence: dict
    created_at: datetime


class WorkItemRecoveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_id: UUID
    actor: str
    reason: str
    command: dict
    prior_outcome: dict
    accepted_revision: int
    accepted_run_revision: int | None
    state: str
    detail: str
    created_at: datetime
    refusal_reason: str | None = None
    events: list[RecoveryEventRead] = Field(default_factory=list)


class WorkItemRecoveryList(BaseModel):
    items: list[WorkItemRecoveryRead]
    total_count: int
