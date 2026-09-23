"""Explicit input and bounded output contracts for public tools."""

from datetime import datetime
from uuid import UUID

from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest, PipelineRunSummary
from app.features.project_management.projects.schemas import GitHubProjectConnection, ProjectUpdate, ProjectWrite
from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(Input):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of returned items")


class Search(Page):
    search: str = Field(default="", max_length=255, description="Filter by project name or owner/repository")


class Items[T](BaseModel):
    items: list[T]
    total_count: int


class ProjectId(Input):
    project_id: UUID


class CreateProject(Input):
    project: ProjectWrite


class UpdateProject(ProjectId):
    project: ProjectUpdate


class ProjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    enabled: bool
    revision: int
    github: GitHubProjectConnection | None


class RunId(Input):
    run_id: UUID


class RunFilter(Page):
    project_id: UUID | None = None
    state: PipelineRunState | None = None
    search: str = Field(default="", max_length=255)


class Enroll(ProjectId):
    pull_request: EnrollPullRequest


class Pause(RunId):
    reason: str = Field(default="Paused through MCP", min_length=1, max_length=500)


class RunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    ai_catalog_id: UUID
    pull_number: int
    pull_url: str
    state: PipelineRunState
    pause_reason: str | None
    revision: int
    next_action_at: datetime | None
    updated_at: datetime


class AttemptFilter(RunId, Page):
    pass


class AttemptView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    attempt_number: int
    kind: str
    state: str
    conversation_url: str | None
    failure_code: str | None
    failure_detail: str | None
    started_at: datetime | None
    finished_at: datetime | None


class AttemptList(Items[AttemptView]):
    summary: PipelineRunSummary


class CatalogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    name: str
    kind: str
    enabled: bool
    availability_state: str
    available_at: datetime | None
    effective_concurrency: int
    active_dispatch_count: int
    pipeline_delivery: bool
    connection_test: bool


class ConnectorView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    provider: str
    enabled: bool
    has_credentials: bool


class StartTest(ProjectId):
    request_id: UUID = Field(description="Generate once for this test and reuse on retries")
    ai_catalog_id: UUID | None = None


class TestId(ProjectId):
    test_id: UUID


class TestView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    ai_catalog_id: UUID | None
    status: str
    phase: str
    cleanup_status: str
    detail: str | None
    configuration_current: bool
    cancel_requested: bool
    deadline: datetime
    finished_at: datetime | None
