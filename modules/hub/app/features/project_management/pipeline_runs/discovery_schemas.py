from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DecisionKind = Literal[
    "run-question",
    "native-hub-question",
    "native-worker-question",
    "native-workflow",
    "native-proposal",
    "native-integration",
]


class DecisionEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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


class DecisionPage(BaseModel):
    items: list[DecisionEntryRead]
    has_more: bool
    next_cursor: str | None


class DecisionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    fingerprint: str
