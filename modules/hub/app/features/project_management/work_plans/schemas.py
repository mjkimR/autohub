import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_graph(graph: dict) -> None:
    remaining = {key: set(parents) for key, parents in graph.items()}
    if any(parent not in remaining for parents in remaining.values() for parent in parents):
        raise ValueError("Dependency target does not exist in this scope")
    while remaining:
        ready = {key for key, parents in remaining.items() if not parents}
        if not ready:
            raise ValueError("Dependencies must not contain cycles or self references")
        remaining = {key: parents - ready for key, parents in remaining.items() if key not in ready}


class WorkItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    key: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}$")
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=16000)
    acceptance: str = Field(default="", max_length=8000)
    depends_on: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def reject_agent_triggers(self):
        if re.search(r"@(?:codex|auto-run)\b", f"{self.title}\n{self.description}\n{self.acceptance}", re.I):
            raise ValueError("AutoHub sends agent requests; omit agent mentions from the specification")
        if len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("Dependencies must be unique")
        return self


class WorkPlanWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=16000)
    base_branch: str = Field(default="main", min_length=1, max_length=255)
    scheduled_at: AwareDatetime | None = Field(
        default=None,
        description="Earliest start time with timezone; null allows immediate execution. Dependencies and capacity still apply.",
    )
    depends_on: list[UUID] = Field(default_factory=list, max_length=100)
    items: list[WorkItemWrite] = Field(default_factory=list, max_length=100)

    @field_validator("scheduled_at")
    @classmethod
    def schedule_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None

    @field_validator("base_branch")
    @classmethod
    def valid_branch(cls, value: str) -> str:
        if (
            value.startswith(("-", "/", "."))
            or value.endswith(("/", ".", ".lock"))
            or any(x in value for x in ("..", "@{", "//", "\\"))
            or re.search(r"[\s~^:?*\[\x00-\x1f\x7f]", value)
            or any(part.startswith(".") or part.endswith(".lock") for part in value.split("/"))
        ):
            raise ValueError("Invalid target branch")
        return value

    @model_validator(mode="after")
    def dependencies(self):
        keys = [item.key for item in self.items]
        if len(keys) != len(set(keys)) or len(self.depends_on) != len(set(self.depends_on)):
            raise ValueError("Item keys and dependencies must be unique")
        validate_graph({item.key: item.depends_on for item in self.items})
        return self

    def require_ready(self) -> None:
        if not self.items or any(not all((item.title, item.description, item.acceptance)) for item in self.items):
            raise ValueError("At least one item is required, with title, specification and acceptance for every item")


class WorkPlanCreate(WorkPlanWrite):
    state: Literal["draft", "proposed", "paused", "active"] = "active"
    request_id: UUID | None = Field(
        default=None,
        description="Reuse on retries to recover the original plan; different content with the same key conflicts",
    )

    @model_validator(mode="after")
    def ready_unless_draft(self):
        if self.state != "draft":
            self.require_ready()
        return self


class PlanControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["pause", "resume", "revoke", "propose", "draft", "ready"]
    expected_revision: int = Field(ge=1)
    reason: str = Field(default="", max_length=4000)


class WorkPlanUpdate(WorkPlanWrite):
    expected_revision: int = Field(ge=1)
    reason: str = Field(default="", max_length=4000)


class IssueMirrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_serialization_defaults_required=True)
    issue_url: str | None
    error: str | None
    pending: bool


class WorkItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_serialization_defaults_required=True)
    id: UUID
    key: str
    title: str
    description: str
    acceptance: str
    state: str
    detail: str | None
    depends_on: list[str] = Field(default_factory=list)
    pipeline_run_id: UUID | None
    pipeline_run_retired_at: datetime | None
    pull_url: str | None
    merge_sha: str | None
    started_at: datetime | None
    completed_at: datetime | None
    issue: IssueMirrorRead | None = None


class WorkPlanRead(BaseModel):
    registration_request_id: UUID | None = None
    model_config = ConfigDict(from_attributes=True, json_schema_serialization_defaults_required=True)
    id: UUID
    project_id: UUID
    title: str
    description: str
    base_branch: str
    state: str
    revision: int
    created_at: datetime
    scheduled_at: datetime | None
    completed_at: datetime | None
    depends_on: list[UUID] = Field(default_factory=list)
    items: list[WorkItemRead] = Field(default_factory=list)
    issue: IssueMirrorRead | None = None

    @field_validator("scheduled_at")
    @classmethod
    def schedule_utc(cls, value: datetime | None) -> datetime | None:
        # SQLite returns naive UTC values for timezone-aware database columns.
        if value is not None:
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return None


class WorkPlanList(BaseModel):
    items: list[WorkPlanRead]
    total_count: int
