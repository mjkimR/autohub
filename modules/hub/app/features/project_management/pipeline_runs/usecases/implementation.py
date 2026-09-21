from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.adapters.base import AgentReply, DeliveryTarget, ExecutionAdapter
from app.features.project_management.pipeline_runs.adapters.registry import (
    resolve_execution_adapter,
)
from app.features.project_management.pipeline_runs.models import (
    ExecutionAttemptState,
    ExecutionDelivery,
    ExecutionReply,
    PipelineRun,
    PipelineRunState,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    PipelineRunRead,
    PullRequestSnapshot,
)
from app.features.project_management.pipeline_runs.usecases.transitions import (
    as_utc,
    finish_closed_pull,
)
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ImplementationInput:
    target: DeliveryTarget
    posted_at: datetime | None
    delivered_head: str
    adapter: ExecutionAdapter


@dataclass(frozen=True)
class ImplementationObservation:
    pull: dict[str, Any]
    replies: list[AgentReply]


class ImplementationProgress:
    def __init__(self, repo: PipelineRunRepository, ai_catalogs: AICatalogService | None):
        self.repo = repo
        self.ai_catalogs = ai_catalogs

    async def prepare(self, session: AsyncSession, run: PipelineRun, target: DeliveryTarget) -> ImplementationInput:
        attempt = await self.repo.active_attempt(session, run.id)
        if attempt is None:
            raise ProjectError(409, "Pipeline run has no active implementation attempt")
        delivery = await self.repo.latest_delivery(session, attempt.id)
        return ImplementationInput(
            target=target,
            posted_at=as_utc(delivery.posted_at) if delivery is not None and delivery.posted_at is not None else None,
            delivered_head=PullRequestSnapshot.model_validate(attempt.request_snapshot["pull_request"]).head_sha,
            adapter=await resolve_execution_adapter(session, run.ai_catalog_id),
        )

    async def observe(
        self, prepared: ImplementationInput, observer: PipelineObservationService
    ) -> ImplementationObservation:
        target = prepared.target
        pr = await observer.get_pull_request(target.connector_id, target.repository, target.pull_number)
        if pr.get("state") == "closed" or (
            prepared.posted_at is not None and pr["head"]["sha"] != prepared.delivered_head
        ):
            return ImplementationObservation(pr, [])
        replies = await prepared.adapter.collect_replies(observer, target, prepared.posted_at)
        return ImplementationObservation(pr, replies)

    async def apply(
        self,
        session: AsyncSession,
        run: PipelineRun,
        now: datetime,
        observed: ImplementationInput,
        result: ImplementationObservation,
    ) -> PipelineRunRead:
        attempt = await self.repo.active_attempt(session, run.id)
        if attempt is None:
            raise ProjectError(409, "Pipeline run has no active implementation attempt")
        delivery = await self.repo.latest_delivery(session, attempt.id)
        pr, replies = result.pull, result.replies
        if pr.get("state") == "closed":
            await finish_closed_pull(self.repo, session, run, pr, now)
            return PipelineRunRead.model_validate(run)
        if observed.posted_at is not None and pr["head"]["sha"] != observed.delivered_head:
            run.state = PipelineRunState.AWAITING_CI
            run.next_action_at = None
            run.revision += 1
            attempt.state = ExecutionAttemptState.RUNNING
            await session.flush()
            return PipelineRunRead.model_validate(run)
        for reply in replies:
            if reply.external_id is not None and not await self.repo.has_reply(session, reply.external_id):
                await self.repo.create_reply(
                    session,
                    ExecutionReply(
                        execution_attempt_id=attempt.id,
                        external_id=reply.external_id,
                        author=reply.author,
                        replied_at=reply.replied_at,
                        excerpt=reply.body.strip()[:500] or None,
                        is_quota_limit=reply.is_quota_limit,
                    ),
                )
        quota_replied_at = max((reply.replied_at for reply in replies if reply.is_quota_limit), default=None)
        if delivery is not None and delivery.posted_at is not None and quota_replied_at is not None:
            run.quota_block_count += 1
            if self.ai_catalogs is not None:
                await self.ai_catalogs.record_quota_event(session, run.ai_catalog_id, quota_replied_at)
            if run.state != PipelineRunState.BLOCKED:
                await self.repo.create_delivery(
                    session,
                    ExecutionDelivery(
                        execution_attempt_id=attempt.id,
                        delivery_number=delivery.delivery_number + 1,
                        cause="quota",
                    ),
                )
                run.state = PipelineRunState.DISPATCHING
            run.next_action_at = None
            run.revision += 1
            await session.flush()
            return PipelineRunRead.model_validate(run)
        if (
            delivery is not None
            and observed.posted_at is not None
            and now - observed.posted_at >= observed.adapter.silent_timeout
        ):
            silent_retries = sum(
                item.cause == "silent" for item in await self.repo.list_deliveries(session, attempt.id)
            )
            if silent_retries >= 1:
                run.state = PipelineRunState.BLOCKED
                run.pause_reason = observed.adapter.silent_block_reason
            else:
                await self.repo.create_delivery(
                    session,
                    ExecutionDelivery(
                        execution_attempt_id=attempt.id,
                        delivery_number=delivery.delivery_number + 1,
                        cause="silent",
                    ),
                )
                run.state = PipelineRunState.DISPATCHING
            run.next_action_at = None
            run.revision += 1
            await session.flush()
            return PipelineRunRead.model_validate(run)

        return PipelineRunRead.model_validate(run)
