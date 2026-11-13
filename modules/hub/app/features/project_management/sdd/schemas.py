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
    display_status: str = Field(description="Descriptive status read from the selected base; not execution eligibility")
    task_kind: str | None = None
    planning_effort: Literal["low", "medium", "high"] | None = None
    dev_effort: Literal["low", "medium", "high"] | None = None
    plan_branch: bool
    dev_branch: bool
    plan_pull: int | None = None
    dev_pull: int | None = None
    run: ProposalRun | None = None
    actions: list[Literal["start_planning", "start_development"]]
    note: str | None = None


class ProposalList(BaseModel):
    base_branch: str
    base_sha: str
    items: list[ProposalState]
    truncated: bool


class ClaimRead(BaseModel):
    id: UUID
    project_id: UUID
    unit: str
    activity: str
    run_id: UUID | None
    settled: bool
    retired: bool
    checkpoint_digest: str
    checkpoint: dict


class ReconcileClaimRequest(BaseModel):
    request_id: UUID
    expected_checkpoint_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    acknowledge_external_work: Literal[True]


class ReconcileRunRequest(BaseModel):
    request_id: UUID
    expected_revision: int = Field(ge=1)
    acknowledge_external_work: Literal[True]
