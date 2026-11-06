"""Persisted decision reads and explicitly write-scoped owner inspection."""

from typing import Literal
from uuid import UUID

from app.features.project_management.pipeline_runs.discovery_repo import DecisionDiscoveryRepository
from app.features.project_management.pipeline_runs.discovery_schemas import (
    DecisionKind,
    DecisionPage,
    DecisionReviewRequest,
)
from app.features.project_management.pipeline_runs.outcome_schemas import Operation
from app.features.project_management.pipeline_runs.usecases.discovery import DecisionDiscoveryUseCase
from app.features.project_management.pipeline_runs.usecases.outcomes import DecisionOutcomeUseCase
from app.mcp.contracts import Input, RunId
from app.mcp.delivery_views import OutcomeView, ReviewView, outcome_view
from app.mcp.dependencies import Dependencies
from app.mcp.registration import register
from app_mcp import ToolRegistry
from pydantic import Field


class DecisionFilter(Input):
    project_id: UUID | None = None
    kind: DecisionKind | None = None
    question_state: Literal["open", "answered"] | None = None
    cursor: str | None = Field(default=None, max_length=4096)
    limit: int = Field(default=20, ge=1, le=100)


class Review(Input, DecisionReviewRequest):
    pass


class Outcome(RunId):
    request_id: UUID
    operation: Operation


def register_decisions(registry: ToolRegistry, deps: Dependencies):
    owner = DecisionDiscoveryUseCase(DecisionDiscoveryRepository())

    async def listing(args: DecisionFilter) -> DecisionPage:
        return await owner.list(args.project_id, args.kind, args.question_state, args.cursor, args.limit)

    async def review(args: Review) -> ReviewView:
        row = await owner.review(args, deps.observer)
        progress = row.sdd_progress or {}
        return ReviewView(
            key=args.key,
            fingerprint=args.fingerprint,
            run_id=row.id,
            project_id=row.project_id,
            state=row.state,
            revision=row.revision,
            inspected_head=progress.get("head_sha"),
            inspected_digest=progress.get("evidence_digest"),
        )

    async def outcome(args: Outcome) -> OutcomeView:
        return outcome_view(await DecisionOutcomeUseCase().get(args.run_id, args.request_id, args.operation))

    register(
        registry,
        "decisions_list",
        "List bounded persisted pending decisions. No live provider inspection or execution.",
        DecisionFilter,
        DecisionPage,
        listing,
    )
    register(
        registry,
        "decisions_review",
        "Inspect the exact key/fingerprint. WRITE: may persist native inspection and increment revision; never approves or resumes. Changed selection refuses.",
        Review,
        ReviewView,
        review,
        write=True,
    )
    register(
        registry,
        "runs_decision_outcome",
        "Read exact run/request/operation outcome. Missing evidence stays unknown; no retry or execution.",
        Outcome,
        OutcomeView,
        outcome,
    )
