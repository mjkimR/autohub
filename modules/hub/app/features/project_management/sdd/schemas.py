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


class ProposalRun(BaseModel):
    id: str
    state: str
    revision: int
    pause_reason: str | None = None
    pull_number: int
    head_sha: str | None = None
    plan_accept_open: bool
    decided: bool


class ProposalState(BaseModel):
    slug: str
    id: str
    path: str
    title: str
    status: str = Field(description="The proposal's status on the base branch")
    display_status: str = Field(description="reviewing while plan-<slug> exists for a draft (no base commit)")
    task_kind: str | None = None
    planning_effort: Literal["low", "medium", "high"] | None = None
    dev_effort: Literal["low", "medium", "high"] | None = None
    plan_branch: bool
    dev_branch: bool
    plan_pull: int | None = None
    dev_pull: int | None = None
    run: ProposalRun | None = None
    actions: list[Literal["start_planning", "accept", "reject", "start_development"]]
    note: str | None = None


class ProposalList(BaseModel):
    base_branch: str
    base_sha: str
    items: list[ProposalState]
    truncated: bool


class SddWarning(BaseModel):
    """A best-effort finding that did not stop the evaluation (a stale receipt, a runtime revision mismatch)."""

    code: str
    detail: str


class SddDiagnostic(BaseModel):
    """Hub-owned guidance selected by a recognized devkit code, never raw repository output."""

    code: str
    severity: Literal["error", "warning", "info"]
    category: Literal["repository", "runtime", "decision"]
    message: str
    action: str
    retry: Literal["after_fix", "safe", "never"]
    target_files: list[str] = Field(default_factory=list)


class SddRuntimeStatus(BaseModel):
    """The host probe (an interpreter started inside the sandbox) and the project head's locked runtime state."""

    ok: bool
    profile: str = "repository-lock"
    state: Literal["ready", "preparing", "failed"] | None = Field(
        default=None, description="Lock-derived runtime of the default-branch head; empty without a connection"
    )
    identity: str | None = None
    bundles: list[str] = Field(default_factory=list)
    provider: str | None = None
    lock_sha256: str | None = None
    revisions: dict[str, str] = Field(default_factory=dict)
    isolation: str | None = None
    detail: str | None = None
    lock_detail: str | None = None


class SddReadiness(BaseModel):
    ready: bool
    reason: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None
    cli_version: str | None = None
    workflow: dict = Field(default_factory=dict)
    current: dict = Field(default_factory=dict)
    warnings: list[SddWarning] = Field(default_factory=list)
    diagnostics: list[SddDiagnostic] = Field(default_factory=list)
    policy: dict = Field(default_factory=dict)


class MilestonePreviewRequest(BaseModel):
    ref: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")
    milestone_id: str = Field(pattern=r"^MS-[A-Za-z0-9_-]+$", max_length=255)
    milestone_path: str | None = Field(default=None, max_length=1024)


class MilestoneMember(BaseModel):
    planning_effort: Literal["low", "medium", "high"] | None = None
    dev_effort: Literal["low", "medium", "high"] | None = None
    id: str
    path: str
    title: str = ""
    status: str
    activity_kind: Literal["plan", "dev"] | None = None
    stage: str | None = None
    admission: Literal["pass", "held", "unknown"]
    scheduling: Literal["pass", "held"]
    workflow_hold: dict = Field(default_factory=dict)
    eligibility: Literal["eligible_now", "held", "existing_activity", "finished", "unsupported", "unknown"]
    reasons: list[str]
    evidence: list[dict] = Field(default_factory=list)
    evidence_observed_at: str | None = None


class MilestonePreview(BaseModel):
    default_catalog: str | None = None
    project_id: str
    repository: str
    requested_ref: str
    resolved_sha: str
    milestone: dict
    observed_at: str
    runtime_identity: str | None = None
    complete: bool
    counts: dict[str, int]
    limits: dict[str, int]
    reasons: list[str]
    warnings: list[SddWarning]
    nodes: list[dict]
    edges: list[dict]
    members: list[MilestoneMember]


class MilestoneList(BaseModel):
    resolved_sha: str
    complete: bool
    reasons: list[str]
    items: list[dict]
