"""Bounded work-item reconciliation; all GitHub I/O occurs outside transactions."""

import asyncio
from datetime import timedelta
from uuid import UUID

from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PullRequestSnapshot
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc, finish_closed_pull
from app.features.project_management.pipelines import services as github_services
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.models import Project
from app.features.project_management.work_plans.execution_repo import WorkExecutionRepository
from app.features.project_management.work_plans.github import MissingWorkBaseBranch, WorkGitHub
from app.features.project_management.work_plans.mirror_records import refresh_mirrors
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import select


class WorkPlanExecution:
    def __init__(self, observer: PipelineObservationService):
        self.observer, self.repo = observer, WorkExecutionRepository()

    async def advance_project(self, project_id: UUID, *, limit: int = 4) -> None:
        # Observation and admission have separate budgets: long-running work must
        # not starve ready items when the catalog has more slots than a tick batch.
        for phase in ("observe", "admit"):
            for _ in range(limit):
                async with AsyncTransaction() as session:
                    claimed = await self.repo.claim(session, project_id, phase=phase)
                if claimed is None:
                    break
                await self.advance(*claimed)

    async def advance(self, plan: WorkPlan, item: WorkItem) -> None:
        try:
            async with asyncio.timeout(45):
                token = await self.observer.get_token(plan.connector_id, "github")
                async with github_services.create_github_client(token) as client:
                    github = WorkGitHub(client)
                    if item.state == "preparing":
                        await self.prepare(plan, item, github)
                    else:
                        await self.observe(plan, item, github)
        except Exception as exc:
            detail = str(exc) if isinstance(exc, GitHubObservationError) else "Work reconciliation failed; will retry"
            delay = exc.retry_after if isinstance(exc, GitHubObservationError) else None
            async with AsyncTransaction() as session:
                current = await self.repo.leased(session, item.id, item.lease_token)
                if current:
                    current.detail = detail
                    current.next_action_at = get_current_utc_time() + timedelta(seconds=delay or 300)
                    if current.state == "preparing" and isinstance(exc, MissingWorkBaseBranch):
                        # Only a confirmed missing base before writes is terminal.
                        # Raw HTTP errors, including reconciliation reads, remain retryable.
                        current.state = "preparation_failed"
                        current.next_action_at = None
            logger.warning(f"Work item {item.id}: {detail}")
        finally:
            async with AsyncTransaction() as session:
                saved_plan = await session.get(WorkPlan, plan.id, with_for_update=True)
                current = await self.repo.leased(session, item.id, item.lease_token)
                if current:
                    current.lease_token, current.lease_expires_at = None, None
                assert saved_plan is not None
                await self.complete_plan(session, saved_plan)
                await refresh_mirrors(session, saved_plan)

    async def prepare(self, plan: WorkPlan, item: WorkItem, github: WorkGitHub) -> None:
        if item.base_sha is None:
            sha = await github.base_sha(plan)
            async with AsyncTransaction() as session:
                current = await self.repo.leased(session, item.id, item.lease_token)
                if current is None:
                    return
                current.base_sha = sha
            item.base_sha = sha
        pull = await github.prepare(plan, item)
        async with AsyncTransaction() as session:
            current = await self.repo.leased(session, item.id, item.lease_token)
            if current is None:
                return
            project = await session.get(Project, plan.project_id)
            assert project is not None
            if project.github_repository != plan.repository or project.github_connector_id != plan.connector_id:
                current.detail = "Project connection changed; restore it to continue preparation"
                return
            current.pull_number, current.pull_url = pull["number"], pull["html_url"]
            if current.pipeline_run_id is None:
                run = await session.scalar(
                    select(PipelineRun)
                    .where(
                        PipelineRun.project_id == plan.project_id,
                        PipelineRun.pull_number == pull["number"],
                    )
                    .order_by(PipelineRun.created_at.desc())
                    .limit(1)
                )
                if run is None:
                    run = PipelineRun(
                        project_id=plan.project_id,
                        ai_catalog_id=current.ai_catalog_id,
                        requested_catalog_id=current.ai_catalog_id,
                        project_revision=project.revision,
                        github_repository=plan.repository,
                        github_connector_id=plan.connector_id,
                        pull_number=pull["number"],
                        pull_url=pull["html_url"],
                        branch=current.branch,
                        state="awaiting_ci" if pull.get("state") == "closed" else "queued",
                        revision=1,
                        pull_snapshot=PullRequestSnapshot(
                            number=pull["number"],
                            url=pull["html_url"],
                            title=current.title,
                            # Local immutable specification; Issue edits are never execution input.
                            body=f"{current.description}\n\nAcceptance criteria:\n{current.acceptance}\n\n"
                            f"Remove `.autohub/work-items/{current.id}.md` when implementing.",
                            base_ref=plan.base_branch,
                            head_ref=str(current.branch),
                            head_sha=pull["head"]["sha"],
                        ).model_dump(mode="json"),
                    )
                    session.add(run)
                    await session.flush()
                current.pipeline_run_id = current.execution_id = run.id
            current.state, current.detail = "running", None

    async def observe(self, plan: WorkPlan, item: WorkItem, github: WorkGitHub) -> None:
        async with AsyncTransaction() as session:
            run = await session.get(PipelineRun, item.pipeline_run_id) if item.pipeline_run_id else None
        if run is None:
            async with AsyncTransaction() as session:
                current = await self.repo.leased(session, item.id, item.lease_token)
                if current:
                    current.state, current.detail = "attention", "Execution is missing without a confirmed completion"
            return
        # Observe even a paused run: manual merges must release dependencies without resuming an agent.
        pull = await github.reader._get(f"/repos/{plan.repository}/pulls/{run.pull_number}")
        valid = (
            pull.get("base", {}).get("ref") == plan.base_branch
            and str((pull.get("base", {}).get("repo") or {}).get("full_name", "")).lower() == plan.repository
            and pull.get("head", {}).get("ref") == item.branch
        )
        async with AsyncTransaction() as session:
            saved_run = await session.get(PipelineRun, run.id, with_for_update=True)
            current = await self.repo.leased(session, item.id, item.lease_token)
            if current is None:
                return
            if saved_run is None:
                current.state, current.detail = "attention", "Execution disappeared during observation"
                return
            now = get_current_utc_time()
            if not valid:
                current.state, current.detail = "attention", "PR identity or target branch changed"
            elif pull.get("merged") is True and pull.get("merge_commit_sha"):
                current.state, current.detail = "succeeded", None
                current.merge_sha, current.completed_at = pull["merge_commit_sha"], now
                if saved_run.lease_expires_at is None or as_utc(saved_run.lease_expires_at) <= now:
                    await finish_closed_pull(PipelineRunRepository(), session, saved_run, pull, now)
            else:
                current.state = (
                    saved_run.state if saved_run.state in ("failed", "blocked", "paused", "canceled") else "running"
                )
                current.detail = saved_run.pause_reason
                if pull.get("state") == "closed":
                    current.state, current.detail = "canceled", "PR closed without a confirmed merge"

    @staticmethod
    async def complete_plan(session, plan: WorkPlan) -> None:
        items = await WorkPlanRepository().items(session, plan.id)
        if plan.state in ("active", "paused") and items and all(item.state == "succeeded" for item in items):
            plan.state, plan.completed_at = "completed", get_current_utc_time()
            plan.revision += 1
