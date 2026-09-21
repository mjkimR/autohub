from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.project_management.pipeline_runs.models import (
    ExecutionAttemptKind,
    ExecutionAttemptState,
    PipelineRunState,
)
from app_layer_base.base.schemas.mixin import TimestampSchemaMixin, UUIDSchemaMixin
from pydantic import BaseModel, ConfigDict, Field

MAX_LINKED_ISSUES = 10


class LinkedIssue(BaseModel):
    number: int = Field(gt=0)
    title: str
    body: str | None = None
    url: str


class PullRequestSnapshot(BaseModel):
    """The task specification: the PR as the user wrote it, plus the issues it closes."""

    number: int = Field(gt=0)
    url: str
    title: str
    body: str | None = None
    base_ref: str
    head_ref: str
    head_sha: str
    linked_issues: list[LinkedIssue] = Field(default_factory=list, max_length=MAX_LINKED_ISSUES)


class EnrollPullRequest(BaseModel):
    pull_number: int = Field(gt=0)
    catalog: str | None = Field(
        default=None,
        max_length=100,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="AI catalog to deliver this run: a catalog key, or a kind ('codex') when exactly one enabled "
        "catalog has it; empty follows the project's selection",
    )
    implemented: bool = Field(
        default=False,
        description="The pull request already holds its implementation (for example, an agent session opened it); "
        "skip the implementation request and start by observing CI",
    )


class PipelineRunRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    ai_catalog_id: UUID
    requested_catalog_id: UUID | None = None
    project_revision: int
    pull_number: int
    pull_url: str
    pull_snapshot: PullRequestSnapshot
    state: PipelineRunState
    pause_reason: str | None
    branch: str
    revision: int
    epoch: int
    lease_owner: str | None
    lease_expires_at: datetime | None
    next_action_at: datetime | None
    quota_block_count: int


class ExecutionAttemptRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    pipeline_run_id: UUID
    attempt_number: int = Field(ge=1)
    epoch: int = Field(ge=1)
    kind: ExecutionAttemptKind
    state: ExecutionAttemptState
    request_snapshot: dict
    request_digest: str
    idempotency_key: UUID
    external_correlation_id: str | None
    external_status: str | None
    conversation_url: str | None
    started_at: datetime | None
    finished_at: datetime | None
    failure_code: str | None
    failure_detail: str | None


class ExecutionDeliveryRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    execution_attempt_id: UUID
    delivery_number: int = Field(ge=1)
    cause: Literal["initial", "silent", "quota", "resume"]
    external_id: str | None
    posted_at: datetime | None


class ExecutionReplyRead(UUIDSchemaMixin, TimestampSchemaMixin):
    model_config = ConfigDict(from_attributes=True)

    execution_attempt_id: UUID
    external_id: str
    author: str
    replied_at: datetime
    excerpt: str | None
    is_quota_limit: bool


class PipelineRunList(BaseModel):
    items: list[PipelineRunRead]
    total_count: int


class PipelineRunSummary(BaseModel):
    """What a run has cost so far: how often an agent was asked, and how long the run has taken."""

    attempts_by_kind: dict[str, int]
    # Requests actually posted to an agent, across every attempt; a retried or resumed attempt posts more than one.
    requests_sent: int
    quota_limit_replies: int
    started_at: datetime
    # When the run reached a final state; empty while it is active.
    finished_at: datetime | None
    elapsed_seconds: int


class ExecutionAttemptList(BaseModel):
    items: list[ExecutionAttemptRead]
    total_count: int
    summary: PipelineRunSummary


class LeaseRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    ttl_seconds: int = Field(default=60, ge=15, le=900)


class LeaseCredential(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    token: UUID


class LeaseMutation(LeaseCredential):
    ttl_seconds: int = Field(default=60, ge=15, le=900)


class LeaseGrant(BaseModel):
    run_id: UUID
    owner: str
    token: UUID
    expires_at: datetime
    run_revision: int


class ImplementationRequest(BaseModel):
    version: Literal[2] = 2
    kind: Literal["implementation", "ci-fix", "conflict-fix"] = "implementation"
    correlation_marker: str
    repository: str
    pull_request: PullRequestSnapshot
    instructions: str


class PrepareImplementationAttempt(LeaseCredential):
    expected_run_revision: int = Field(ge=1)


class PreparedImplementationAttempt(BaseModel):
    attempt: ExecutionAttemptRead
    request: ImplementationRequest
    run_revision: int
    created: bool


class PauseRunRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AttachPRRequest(BaseModel):
    pull_number: int = Field(gt=0)
    pull_url: str | None = Field(default=None, max_length=1000)


class CompleteAttemptRequest(BaseModel):
    status: Literal["completed", "failed"]
    failure_code: str | None = Field(default=None, max_length=100)
    failure_detail: str | None = Field(default=None, max_length=2000)
