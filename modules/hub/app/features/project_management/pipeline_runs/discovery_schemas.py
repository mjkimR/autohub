from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DecisionKind = Literal["run-question",]
SddActivityKind = Literal["plan", "dev"]


class DecisionEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    run_state: str
    pull_number: int
    pull_url: str
    key: str
    run_id: UUID
    project_id: UUID
    kind: DecisionKind
    subject_id: str
    fingerprint: str
    title: str
    question_state: str | None
    actionable: bool
    waiting_since: datetime
    observed_at: datetime
    revision: int
    head_sha: str | None
    sdd_activity: SddActivityKind | None = Field(
        default=None,
        description="plan or dev, as retained in the owning Run's sdd_snapshot (dev when it records no kind); null for an ordinary Run or an unrecognized kind",
    )
    sdd_unit: str | None = Field(
        default=None,
        description="SDD unit (spec_dir) retained in the owning Run's sdd_snapshot; null for an ordinary Run",
    )


class DecisionPage(BaseModel):
    items: list[DecisionEntryRead]
    has_more: bool
    next_cursor: str | None
    # Actionable rows the filters admit, independent of cursor and limit.
    actionable_total_count: int


class DecisionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    fingerprint: str
