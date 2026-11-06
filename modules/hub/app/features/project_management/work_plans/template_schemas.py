from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.project_management.work_plans.schemas import WorkPlanCreate, WorkPlanRead, WorkPlanWrite
from pydantic import BaseModel, ConfigDict, Field, model_validator

Operation = Literal["create", "from-plan", "update", "delete", "register"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TemplateItem(Strict):
    key: str
    title: str = ""
    description: str = ""
    acceptance: str = ""
    depends_on: list[str] = Field(default_factory=list, max_length=100)


class TemplateDefinition(Strict):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=16000)
    base_branch: str = Field(default="main", min_length=1, max_length=255)
    items: list[TemplateItem] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_owner(self):
        WorkPlanWrite.model_validate(self.model_dump())
        return self


class TemplateCreate(Strict):
    request_id: UUID
    name: str = Field(min_length=1, max_length=200)
    definition: TemplateDefinition


class TemplateUpdate(TemplateCreate):
    expected_revision: int = Field(ge=1)


class TemplateDelete(Strict):
    request_id: UUID
    expected_revision: int = Field(ge=1)


class TemplateFromPlan(Strict):
    request_id: UUID
    name: str = Field(min_length=1, max_length=200)
    source_plan_id: UUID
    expected_revision: int = Field(ge=1)


class TemplateRegistration(Strict):
    request_id: UUID
    template_revision: int = Field(ge=1)
    template_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_repository: str
    expected_connector_id: UUID
    payload: WorkPlanCreate

    @model_validator(mode="after")
    def matching_request(self):
        if self.payload.request_id != self.request_id:
            raise ValueError("Registration and owner request IDs must match")
        return self


class WorkPlanTemplateRead(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    revision: int
    deleted: bool
    schema_version: int
    definition: TemplateDefinition
    digest: str
    created_actor: str
    updated_actor: str
    created_at: datetime
    updated_at: datetime


class TemplateList(BaseModel):
    items: list[WorkPlanTemplateRead]
    total_count: int


class TemplateOutcome(BaseModel):
    refresh_error: str | None = None
    record_state: Literal["unknown", "recorded"]
    operation: Operation
    request_id: UUID
    original_template: WorkPlanTemplateRead | None = None
    current_template: WorkPlanTemplateRead | None = None
    original_plan: WorkPlanRead | None = None
    current_plan: WorkPlanRead | None = None
    source_plan_id: UUID | None = None
    source_revision: int | None = None
    repository: str | None = None
    connector_id: UUID | None = None
    reviewed_payload: WorkPlanCreate | None = None
    omitted: list[str] = Field(default_factory=list)
