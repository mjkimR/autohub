from __future__ import annotations

from datetime import datetime

from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.adapters.base import DeliveryTarget
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
from app.features.project_management.projects.models import Project
from sqlalchemy.ext.asyncio import AsyncSession


class ImplementationProgress:
    def __init__(self, repo: PipelineRunRepository, ai_catalogs: AICatalogService | None):
        self.repo = repo
        self.ai_catalogs = ai_catalogs

    async def advance(
        self,
        session: AsyncSession,
        run: PipelineRun,
        project: Project,
        now: datetime,
        observer: PipelineObservationService,
    ) -> PipelineRunRead:
        if project.github_connector_id is None or project.github_repository is None:
            raise ProjectError(422, "Project missing GitHub connection for pipeline run")
        attempt = await self.repo.active_attempt(session, run.id)
        if attempt is None:
            raise ProjectError(409, "Pipeline run has no active implementation attempt")
        delivery = await self.repo.latest_delivery(session, attempt.id)
        posted_at = as_utc(delivery.posted_at) if delivery is not None and delivery.posted_at is not None else None
        pr = await observer.get_pull_request(project.github_connector_id, project.github_repository, run.pull_number)
        if pr.get("state") == "closed":
            await finish_closed_pull(self.repo, session, run, pr, now)
            return PipelineRunRead.model_validate(run)
        delivery_head = PullRequestSnapshot.model_validate(attempt.request_snapshot["pull_request"]).head_sha
        if delivery is not None and delivery.posted_at is not None and pr["head"]["sha"] != delivery_head:
            run.state = PipelineRunState.AWAITING_CI
            run.next_action_at = None
            run.revision += 1
            attempt.state = ExecutionAttemptState.RUNNING
            await session.flush()
            return PipelineRunRead.model_validate(run)
        target = DeliveryTarget(project.github_connector_id, project.github_repository, run.pull_number)
        adapter = await resolve_execution_adapter(session, run.ai_catalog_id)
        replies = await adapter.collect_replies(observer, target, posted_at)
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
        if delivery is not None and posted_at is not None and now - posted_at >= adapter.silent_timeout:
            silent_retries = sum(
                item.cause == "silent" for item in await self.repo.list_deliveries(session, attempt.id)
            )
            if silent_retries >= 1:
                run.state = PipelineRunState.BLOCKED
                run.pause_reason = adapter.silent_block_reason
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
