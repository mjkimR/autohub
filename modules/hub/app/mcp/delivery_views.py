"""Explicit public projections; owner snapshots never pass through."""

from datetime import datetime
from uuid import UUID

from app.features.project_management.pipeline_runs.outcome_schemas import Operation
from pydantic import BaseModel, ConfigDict, Field


class View(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReviewView(View):
    key: str
    fingerprint: str
    run_id: UUID
    project_id: UUID
    state: str
    revision: int
    inspected_head: str | None = None
    requires_reselection: bool = False


class OutcomeView(View):
    operation: Operation
    request_id: UUID
    run_id: UUID
    record_state: str
    run_revision: int
    run_state: str
    observed_at: datetime
    question_id: UUID | None = None
    answer_id: UUID | None = None
    applied_attempt_id: UUID | None = None
    execution_state: str | None = None
    delivery_state: str | None = None
    delivery_at: datetime | None = None
    inspected_head: str | None = None
    unavailable_reason: str | None = None


def outcome_view(row) -> OutcomeView:
    return OutcomeView.model_validate(row.model_dump())


class RecoveryEvent(View):
    id: UUID
    kind: str
    detail: str
    created_at: datetime


class RecoveryView(View):
    id: UUID
    request_id: UUID
    actor: str
    reason: str
    accepted_revision: int
    accepted_run_revision: int | None
    state: str
    detail: str
    created_at: datetime
    refusal_reason: str | None = None
    events: list[RecoveryEvent] = Field(max_length=100)
    event_count: int
    events_omitted: bool


def recovery_view(row) -> RecoveryView:
    return RecoveryView.model_validate(
        row.model_dump()
        | {
            "events": row.events[:100],
            "event_count": len(row.events),
            "events_omitted": len(row.events) > 100,
        }
    )


class RecoveryPage(View):
    items: list[RecoveryView] = Field(max_length=100)
    total_count: int


class RecoveredItem(View):
    id: UUID
    state: str
    pipeline_run_id: UUID | None


class RecoveryResult(View):
    recovery: RecoveryView
    item: RecoveredItem
