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
    inspected_digest: str | None = None
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
    native_channel: str | None = None
    publication_state: str | None = None
    candidate_heads: list[str] = Field(default_factory=list, max_length=50)
    candidate_head_count: int = 0
    candidate_heads_omitted: bool = False
    candidate_head: str | None = None
    resolved_envelope: str | None = None
    inspected_head: str | None = None
    inspected_digest: str | None = None
    current_authority_present: bool = False
    current_hold_present: bool = False
    unavailable_reason: str | None = None


def outcome_view(row) -> OutcomeView:
    data = row.model_dump()
    heads = data.pop("candidate_heads")
    return OutcomeView.model_validate(
        data
        | {
            "candidate_heads": heads[:50],
            "candidate_head_count": len(heads),
            "candidate_heads_omitted": len(heads) > 50,
            "current_authority_present": row.current_authority is not None,
            "current_hold_present": row.current_hold is not None,
        }
    )


class ClaimView(View):
    id: UUID
    activity: str
    settled: bool
    uncertain: bool
    uncertainty_reason: str | None = None
    uncertainty_observed_at: str | None = None
    branch: str | None = None
    initial_sha: str | None = None
    pull_number: int | None = None
    run_id: UUID | None = None


class MemberView(View):
    id: UUID
    anchor_id: str
    path: str
    position: int
    phase: str
    state: str
    spec_anchor: str | None = None
    latest_claim: ClaimView | None = None
    claim_count: int
    history_omitted: bool


class BatchSummary(View):
    id: UUID
    project_id: UUID
    state: str
    revision: int
    exclusion: bool
    detail: str | None
    member_count: int


class BatchView(BatchSummary):
    members: list[MemberView] = Field(max_length=50)
    members_omitted: bool


class BatchList(View):
    items: list[BatchSummary] = Field(max_length=50)
    history_window: int = 50


def batch_summary(row) -> BatchSummary:
    return BatchSummary.model_validate(row | {"member_count": len(row["members"])})


def batch_view(row) -> BatchView:
    members = []
    for member in row["members"][:50]:
        claims = member["claims"]
        members.append(
            MemberView.model_validate(
                member
                | {
                    "latest_claim": claims[-1] if claims else None,
                    "claim_count": len(claims),
                    "history_omitted": len(claims) > 1,
                }
            )
        )
    return BatchView.model_validate(
        batch_summary(row).model_dump()
        | {
            "members": members,
            "members_omitted": len(row["members"]) > 50,
        }
    )


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
