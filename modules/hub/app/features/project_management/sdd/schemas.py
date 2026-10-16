from pydantic import BaseModel, Field

SPEC_PATTERN = r"^specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+$"


class SddInspectionRequest(BaseModel):
    pull_number: int = Field(gt=0)
    spec_dir: str = Field(pattern=SPEC_PATTERN, max_length=255)


class SddWarning(BaseModel):
    """A best-effort finding that did not stop the evaluation (a stale receipt, a runtime revision mismatch)."""

    code: str
    detail: str


class SddReadiness(BaseModel):
    ready: bool
    reason: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None
    cli_version: str | None = None
    workflow: dict = Field(default_factory=dict)
    current: dict = Field(default_factory=dict)
    warnings: list[SddWarning] = Field(default_factory=list)
