"""Read-only exact owner outcome; nullable facts never imply completion."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Operation = Literal["question", "answer", "resume"]


class DecisionOutcome(BaseModel):
    operation: Operation
    request_id: UUID
    run_id: UUID
    record_state: Literal["unknown", "recorded"]
    run_revision: int
    run_state: str
    observed_at: datetime
    question_id: UUID | None = None
    answer_id: UUID | None = None
    answer_text: str | None = None
    applied_attempt_id: UUID | None = None
    execution_state: str | None = None
    delivery_state: Literal["posted", "pending"] | None = None
    delivery_at: datetime | None = None
    inspected_head: str | None = None
    unavailable_reason: str | None = None
