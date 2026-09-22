from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.project_management.connection_tests.adapters.specs import ConnectionTestSpec
from pydantic import BaseModel, ConfigDict, Field


class ResolveCleanup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: UUID
    confirmed_remote_stopped: Literal[True]
    note: str = Field(min_length=1, max_length=1000)
    unrelated_pulls: dict[str, str] = Field(default_factory=dict, max_length=1000)


class StartConnectionTest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    ai_catalog_id: UUID | None = None


class ConnectionTestCatalog(BaseModel):
    id: UUID
    key: str
    name: str
    kind: str
    adapter: str
    revision: int
    connector_id: UUID | None
    configuration_fingerprint: str | None = None
    test_spec: ConnectionTestSpec | None = None


class ConnectionTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    project_revision: int
    repository: str
    ai_catalog_id: UUID | None
    catalog_snapshot: ConnectionTestCatalog | None
    configuration_current: bool = False
    cleanup_resolution_available: bool = False
    test_spec: ConnectionTestSpec | None = None
    status: Literal["running", "succeeded", "failed", "timed_out", "canceled"]
    phase: str
    cleanup_status: Literal["pending", "waiting", "completed", "failed"]
    detail: str | None
    evidence: dict
    cancel_requested: bool
    created_at: datetime
    deadline: datetime
    finished_at: datetime | None


class ConnectionTestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: UUID


class RequirementStatus(BaseModel):
    key: str
    status: Literal["configured", "missing", "manual"]


class ConnectionTestOption(BaseModel):
    ai_catalog_id: UUID
    name: str
    kind: str
    spec: ConnectionTestSpec
    requirements: list[RequirementStatus]
    configuration_fingerprint: str
    ready: bool
