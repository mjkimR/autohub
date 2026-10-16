from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .units import UNIT_PATTERN

SPEC_PATTERN = UNIT_PATTERN  # a spec bundle or a proposal bundle; the name stays for the API fields that use it


class SddInspectionRequest(BaseModel):
    pull_number: int = Field(gt=0)
    spec_dir: str = Field(pattern=SPEC_PATTERN, max_length=255)


class StartActivityRequest(BaseModel):
    """Start Planning or Development of a proposal in the cloud: Hub makes the branch and pull request."""

    request_id: UUID = Field(description="Client UUID; retries after a lost response enroll the same start")
    base_branch: str = Field(default="main", min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
    activity_effort: Literal["low", "medium", "high"] | None = None
    catalog: str | None = Field(default=None, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    actor: str = Field(default="", exclude=True)


class SddWarning(BaseModel):
    """A best-effort finding that did not stop the evaluation (a stale receipt, a runtime revision mismatch)."""

    code: str
    detail: str


class SddRuntimeStatus(BaseModel):
    """The host's SDD runtime: its pin and whether devkit starts inside the sandbox (the new-host canary)."""

    ok: bool
    provider: str | None = None
    lock_sha256: str | None = None
    revisions: dict[str, str] = Field(default_factory=dict)
    isolation: str | None = None
    detail: str | None = None


class SddReadiness(BaseModel):
    ready: bool
    reason: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None
    cli_version: str | None = None
    workflow: dict = Field(default_factory=dict)
    current: dict = Field(default_factory=dict)
    warnings: list[SddWarning] = Field(default_factory=list)
