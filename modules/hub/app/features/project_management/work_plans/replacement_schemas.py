from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReplacementCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    expected_original_revision: int = Field(ge=1)
    expected_replacement_revision: int = Field(ge=1)
    expected_evidence_revision: int = Field(ge=0)

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value):
        if not value.strip():
            raise ValueError("Reason is required")
        return value.strip()


class ReplacementLinkCommand(ReplacementCommand):
    replacement_item_id: UUID


class ReplacementAcceptCommand(ReplacementCommand):
    dependent_item_id: UUID
    original_digest: str
    replacement_digest: str
    merge_sha: str
    execution_id: UUID


class ReplacementWithdrawCommand(ReplacementCommand):
    acceptance_id: UUID | None = None


class ReplacementEndpoint(BaseModel):
    plan_id: UUID
    item_id: UUID
    key: str
    title: str
    description: str
    acceptance: str
    digest: str
    plan_revision: int
    plan_state: str
    item_state: str
    repository: str
    connector_id: UUID
    target: str
    branch: str | None
    execution_id: UUID | None
    pull_number: int | None
    pull_url: str | None
    merge_sha: str | None
    completed_at: str | None


class ReplacementSnapshot(BaseModel):
    original: ReplacementEndpoint
    replacement: ReplacementEndpoint


class ReplacementAcceptanceRead(BaseModel):
    id: UUID
    dependent_item_id: UUID
    active: bool
    consumed: bool
    snapshot: ReplacementSnapshot
    actor: str
    reason: str


class ReplacementEventRead(BaseModel):
    id: UUID
    acceptance_id: UUID | None
    kind: str
    actor: str
    reason: str
    revision: int
    evidence: dict[str, Any]
    created_at: str


class ReplacementLinkRead(BaseModel):
    id: UUID
    active: bool
    snapshot: ReplacementSnapshot
    current_replacement: ReplacementEndpoint
    actor: str
    reason: str
    acceptances: list[ReplacementAcceptanceRead]
    events: list[ReplacementEventRead]
    event_offset: int = 0
    event_total_count: int = 0


class ReplacementResult(BaseModel):
    operation: str
    request_id: UUID
    link_id: UUID
    acceptance_id: UUID | None
    original_revision: int
    evidence_revision: int


class ReplacementRead(BaseModel):
    original: ReplacementEndpoint
    candidate: ReplacementEndpoint | None = None
    evidence_revision: int
    links: list[ReplacementLinkRead]
    history_offset: int = 0
    history_total_count: int = 0
    history_limit: int = 10
    result: ReplacementResult | None = None
