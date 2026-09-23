"""Explicit input and bounded output contracts for public tools."""

from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from app.features.project_management.connection_tests.adapters.specs import COMMON_EVIDENCE
from app.features.project_management.connection_tests.schemas import ConnectionTestOption, ConnectionTestRead
from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest, PipelineRunSummary
from app.features.project_management.projects.schemas import GitHubProjectConnection, ProjectPatch, ProjectWrite
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Page(Input):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of returned items")


class Search(Page):
    search: str = Field(default="", max_length=255, description="Filter by project name or owner/repository")


WAIT_SECONDS = Field(
    default=0, ge=0, le=20, description="Wait up to this many seconds for a state change; 0 returns immediately"
)


class Items[T](BaseModel):
    items: list[T]
    total_count: int


class ProjectId(Input):
    project_id: UUID


class ProjectLookup(Input):
    project_id: UUID | None = None
    repository: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*$",
        max_length=255,
        description="owner/repository, instead of project_id",
    )

    @model_validator(mode="after")
    def exactly_one(self) -> "ProjectLookup":
        if (self.project_id is None) == (self.repository is None):
            raise ValueError("Provide exactly one of project_id or repository")
        return self


class CreateProject(Input):
    project: ProjectWrite


class UpdateProject(ProjectId):
    project: ProjectPatch


class ProjectView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    enabled: bool
    revision: int
    github: GitHubProjectConnection | None
    github_connector_name: str | None = None
    ai_catalog_key: str | None = Field(default=None, description="null means the default Codex catalog")


class RunId(Input):
    run_id: UUID


class RunWait(RunId):
    wait_seconds: int = WAIT_SECONDS


class RunFilter(Page):
    project_id: UUID | None = None
    state: PipelineRunState | None = None
    pull_number: int | None = Field(default=None, gt=0, description="Exact pull request number")
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
    catalog_key: str | None = None
    pull_number: int
    pull_url: str
    state: PipelineRunState
    pause_reason: str | None
    revision: int
    next_action_at: datetime | None
    updated_at: datetime

    @property
    def settled(self) -> bool:
        return self.state in (PipelineRunState.COMPLETED, PipelineRunState.FAILED, PipelineRunState.CANCELED)


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


class TestFilter(ProjectId):
    limit: int = Field(default=10, ge=1, le=30, description="Most recent tests first; at most 30 are kept for listing")


class TestWait(TestId):
    wait_seconds: int = WAIT_SECONDS


CLEANUP_NOTES = ("cleanup_warning", "cleanup_error")


class TestView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    ai_catalog_id: UUID | None
    catalog_key: str | None = None
    status: str
    phase: str
    phase_label: str | None = None
    cleanup_status: str
    detail: str | None
    evidence: dict[str, str] = Field(
        default_factory=dict, description="Test PR, CI and provider links collected so far, plus cleanup notes"
    )
    configuration_current: bool
    cancel_requested: bool
    deadline: datetime
    finished_at: datetime | None

    @classmethod
    def from_read(cls, test: ConnectionTestRead) -> "TestView":
        spec = test.test_spec
        # Raw evidence also holds internal cleanup state; only the spec's public items are exposed.
        view = cls.model_validate(test.model_dump(exclude={"evidence"}))
        view.catalog_key = test.catalog_snapshot.key if test.catalog_snapshot else None
        view.phase_label = spec.phases.get(test.phase) if spec else None
        evidence = {}
        for item in spec.evidence if spec else COMMON_EVIDENCE:
            value = test.evidence.get(item.key)
            if isinstance(value, str) and value and (item.origin is None or trusted_link(value, item.origin)):
                evidence[item.key] = value
        for key in CLEANUP_NOTES:
            if isinstance(note := test.evidence.get(key), str) and note:
                evidence[key] = note
        view.evidence = evidence
        return view

    @property
    def settled(self) -> bool:
        return self.status != "running" and self.cleanup_status in ("completed", "failed")


def trusted_link(value: str, origin: str) -> bool:
    try:
        url = urlsplit(value)
    except ValueError:
        return False
    return f"{url.scheme}://{url.netloc}" == origin and url.username is None and url.password is None


class PendingRequirement(BaseModel):
    key: str
    label: str
    status: str
    description: str
    url: str | None


class ReadinessView(BaseModel):
    ai_catalog_id: UUID
    name: str
    kind: str
    test_title: str
    ready: bool
    pending: list[PendingRequirement] = Field(
        description="Missing requirements, and manual ones AutoHub cannot check; configured ones are omitted"
    )

    @classmethod
    def from_option(cls, option: ConnectionTestOption) -> "ReadinessView":
        labels = {requirement.key: requirement for requirement in option.spec.requirements}
        pending = [
            PendingRequirement(
                key=status.key,
                label=labels[status.key].label if status.key in labels else status.key,
                status=status.status,
                description=labels[status.key].description if status.key in labels else "",
                url=labels[status.key].url if status.key in labels else None,
            )
            for status in option.requirements
            if status.status != "configured"
        ]
        return cls(
            ai_catalog_id=option.ai_catalog_id,
            name=option.name,
            kind=option.kind,
            test_title=option.spec.title,
            ready=option.ready,
            pending=pending,
        )
