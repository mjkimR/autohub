from pydantic import BaseModel, Field

SPEC_PATTERN = r"^specs/[0-9]{4}-[0-9]{2}/[a-zA-Z0-9_-]+$"


class SpecrigInspectionRequest(BaseModel):
    pull_number: int = Field(gt=0)
    spec_dir: str = Field(pattern=SPEC_PATTERN, max_length=255)


class SpecrigReadiness(BaseModel):
    ready: bool
    reason: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None
    cli_version: str | None = None
    workflow: dict = Field(default_factory=dict)
    current: dict = Field(default_factory=dict)
