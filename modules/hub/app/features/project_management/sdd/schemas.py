from pydantic import BaseModel, Field

from .units import UNIT_PATTERN

SPEC_PATTERN = UNIT_PATTERN  # a spec bundle or a proposal bundle; the name stays for the API fields that use it


class SddInspectionRequest(BaseModel):
    pull_number: int = Field(gt=0)
    spec_dir: str = Field(pattern=SPEC_PATTERN, max_length=255)


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
