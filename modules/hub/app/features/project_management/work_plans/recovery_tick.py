"""Fenced recovery phases; remote reads never hold a database transaction."""

import asyncio
from datetime import timedelta
from uuid import uuid4

from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.adapters.base import DeliveryTarget
from app.features.project_management.pipeline_runs.adapters.registry import resolve_execution_adapter
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import ImplementationRequest
from app.features.project_management.pipeline_runs.usecases.catalogs import run_catalog
from app.features.project_management.pipeline_runs.usecases.recovery import activate_recovery
from app.features.project_management.pipeline_runs.usecases.resume_evidence import project_change_push
from app.features.project_management.pipeline_runs.usecases.transitions import (
    EXTERNAL_IMPLEMENTATION_STATUS,
    as_utc,
    finish_closed_pull,
)
from app.features.project_management.pipelines import services
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.work_plans.github import PreparationRefused, WorkGitHub
from app.features.project_management.work_plans.models import (
    ItemDependency,
    PlanDependency,
    WorkItem,
    WorkItemRecovery,
    WorkPlan,
)
from app.features.project_management.work_plans.recovery import PENDING, event
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError


class RecoveryTick:
    def __init__(self, observer):
        self.observer = observer

    async def advance(self, project_id, limit=4):
        async with AsyncTransaction() as session:
            now = get_current_utc_time()
            ids = list(
                await session.scalars(
                    select(WorkItemRecovery.id)
                    .join(WorkItem, WorkItem.id == WorkItemRecovery.item_id)
                    .join(WorkPlan, WorkPlan.id == WorkItemRecovery.plan_id)
                    .where(
                        WorkItemRecovery.project_id == project_id,
                        WorkItemRecovery.state.in_(PENDING),
                        or_(WorkItem.lease_expires_at.is_(None), WorkItem.lease_expires_at <= now),
                        or_(
                            WorkItemRecovery.state == "accepted",
                            WorkItem.next_action_at.is_(None),
                            WorkItem.next_action_at <= now,
                        ),
                        ~and_(
                            WorkItemRecovery.state == "awaiting-admission",
                            WorkItem.pipeline_run_id.is_(None),
                            WorkPlan.revision == WorkItemRecovery.accepted_revision,
                            WorkPlan.state == "active",
                        ),
                    )
                    .order_by(
                        case((WorkItemRecovery.state == "accepted", 0), else_=1),
                        WorkItem.next_action_at.nullsfirst(),
                        WorkItemRecovery.created_at,
                    )
                    .limit(limit)
                )
            )
        for recovery_id in ids:
            await self.one(project_id, recovery_id)

    async def locked(self, session, project_id, recovery_id):
        project = await session.get(Project, project_id, with_for_update=True)
        row = await session.get(WorkItemRecovery, recovery_id)
        if row is None or row.project_id != project_id or row.state not in PENDING:
            return None
        plan = await session.get(WorkPlan, row.plan_id, with_for_update=True)
        item = await session.get(WorkItem, row.item_id)
        run = (
            await session.get(PipelineRun, item.pipeline_run_id, with_for_update=True) if item.pipeline_run_id else None
        )
        item = await session.get(WorkItem, row.item_id, with_for_update=True)
        return project, plan, run, item, row

    async def one(self, project_id, recovery_id):
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            locked = await self.locked(session, project_id, recovery_id)
            if locked is None:
                return
            _project, plan, run, item, row = locked
            if item.lease_expires_at and as_utc(item.lease_expires_at) > now:
                return
            if plan.state != "active" or plan.revision != row.accepted_revision:
                await event(session, row, "refused", "Plan changed; inspect and explicitly reconfirm recovery")
                if row.prior_outcome["run"] is None and item.state == "waiting":
                    item.state, item.detail = "preparation_failed", "Plan changed before recovery admission"
                return
            if row.state == "awaiting-admission" and row.prior_outcome["run"] is None:
                return  # Ordinary preparation admission owns these gates and its lease.
            if run and (run.revision != row.accepted_run_revision or run.state not in ("failed", "canceled")):
                await event(session, row, "refused", "Run changed; inspect existing Run controls")
                return
            if run and run.lease_expires_at and as_utc(run.lease_expires_at) > now:
                return
            if item.next_action_at and as_utc(item.next_action_at) > now and row.state != "accepted":
                return
            item.lease_token, item.lease_expires_at = uuid4(), now + timedelta(seconds=90)
            row.lease_generation += 1
            generation, token = row.lease_generation, item.lease_token
            await event(session, row, "reconciling", "Checking original PR and prior delivery; no new request sent")
            attempts = await PipelineRunRepository().list_attempts(session, run.id) if run else []
            last = attempts[-1] if attempts else None
            delivery = await PipelineRunRepository().latest_delivery(session, last.id) if last else None
            adapter = await resolve_execution_adapter(session, run.ai_catalog_id) if run else None
        try:
            async with asyncio.timeout(45):
                auth = await self.observer.get_token(plan.connector_id, "github")
                async with services.create_github_client(auth) as client:
                    github = WorkGitHub(client)
                    if run:
                        assert adapter is not None
                        pull = await github.reader._get(f"/repos/{plan.repository}/pulls/{run.pull_number}")
                        receipt = None
                        if last and delivery and delivery.posted_at is None:
                            receipt = await adapter.find_delivery(
                                self.observer,
                                DeliveryTarget(plan.connector_id, plan.repository, run.pull_number),
                                ImplementationRequest.model_validate(last.request_snapshot),
                                delivery.delivery_number,
                            )
                        posted_at = receipt.posted_at if receipt else delivery.posted_at if delivery else None
                        implemented = bool(
                            last
                            and (
                                last.external_status == EXTERNAL_IMPLEMENTATION_STATUS
                                or (
                                    posted_at
                                    and last.request_snapshot["pull_request"]["head_sha"] != pull["head"]["sha"]
                                )
                            )
                        )
                        replies = (
                            await adapter.collect_replies(
                                self.observer,
                                DeliveryTarget(plan.connector_id, plan.repository, run.pull_number),
                                as_utc(posted_at),
                            )
                            if posted_at
                            and not implemented
                            and pull.get("state") == "open"
                            and self.valid_pull(plan, item, run, pull)
                            else []
                        )
                        stopped = (
                            last is None
                            or (delivery is None and last.state == "failed")
                            or bool(
                                delivery and delivery.cause != "silent" and any(not r.is_quota_limit for r in replies)
                            )
                        )
                        if last and last.failure_code in (
                            "CI_FAILED",
                            "CI_ENVIRONMENT_FAILURE",
                            "MERGE_FAILED",
                            "MERGE_CONFLICT",
                        ):
                            stopped = True
                        base_sha = None
                    else:
                        base_sha, pull, implemented, stopped = await github.base_sha(plan), None, False, True
            await self.apply(
                project_id,
                recovery_id,
                token,
                generation,
                pull,
                base_sha,
                implemented,
                stopped,
                receipt if run else None,
            )
        except Exception as exc:
            logger.warning(f"Work recovery {recovery_id} deferred: {type(exc).__name__}")
            async with AsyncTransaction() as session:
                locked = await self.locked(session, project_id, recovery_id)
                if locked:
                    _, _, _, current, row = locked
                    if self.owns(current, row, token, generation):
                        if isinstance(exc, PreparationRefused):
                            await event(session, row, "refused", str(exc))
                            current.next_action_at = None
                        else:
                            await event(
                                session,
                                row,
                                "reconciling",
                                "Remote outcome remains uncertain; refresh after reconciliation",
                            )
                            current.next_action_at = get_current_utc_time() + timedelta(seconds=60)
                        current.lease_token = current.lease_expires_at = None

    @staticmethod
    def owns(item, row, token, generation):
        return (
            row.lease_generation == generation
            and item.lease_token == token
            and item.lease_expires_at
            and as_utc(item.lease_expires_at) > get_current_utc_time()
        )

    async def apply(
        self, project_id, recovery_id, token, generation, pull, base_sha, implemented, stopped, receipt=None
    ):
        try:
            async with AsyncTransaction() as session:
                locked = await self.locked(session, project_id, recovery_id)
                if locked is None:
                    return
                project, plan, run, item, row = locked
                if not self.owns(item, row, token, generation):
                    return
                valid_revision = (
                    plan.state == "active"
                    and plan.revision == row.accepted_revision
                    and (run is None or run.revision == row.accepted_run_revision)
                )
                if valid_revision and run and pull and self.valid_pull(plan, item, run, pull):
                    attempts = await PipelineRunRepository().list_attempts(session, run.id)
                    implemented = implemented or await project_change_push(
                        PipelineRunRepository(), session, attempts, pull["head"]["sha"]
                    )
                if valid_revision and receipt and run:
                    latest = await PipelineRunRepository().list_attempts(session, run.id)
                    prior_delivery = (
                        await PipelineRunRepository().latest_delivery(session, latest[-1].id) if latest else None
                    )
                    if prior_delivery and prior_delivery.posted_at is None:
                        prior_delivery.posted_at, prior_delivery.external_id = receipt.posted_at, receipt.external_id
                if (
                    plan.state != "active"
                    or plan.revision != row.accepted_revision
                    or (run and (run.revision != row.accepted_run_revision or run.state not in ("failed", "canceled")))
                ):
                    await event(
                        session, row, "refused", "Plan or Run changed during reconciliation; inspect before retry"
                    )
                elif project.github_repository != plan.repository or project.github_connector_id != plan.connector_id:
                    await event(session, row, "refused", "Repository connection changed; restore original binding")
                elif project.project_type == "sdd":
                    await event(
                        session, row, "refused", "Native sdd project requires a bound spec; use repository controls"
                    )
                elif not run:
                    item.state, item.base_sha, item.detail = (
                        "waiting",
                        base_sha,
                        "Recovery accepted; awaiting admission",
                    )
                    await event(
                        session, row, "awaiting-admission", "Waiting for schedule, dependencies and shared capacity"
                    )
                elif not self.valid_pull(plan, item, run, pull):
                    await event(session, row, "refused", "PR identity or original target changed; inspect PR")
                elif pull.get("merged") is True and pull.get("merge_commit_sha"):
                    await finish_closed_pull(PipelineRunRepository(), session, run, pull, get_current_utc_time())
                    item.state, item.merge_sha, item.completed_at = (
                        "succeeded",
                        pull["merge_commit_sha"],
                        get_current_utc_time(),
                    )
                    item.detail = None
                    await event(session, row, "completed", "Confirmed original-target merge without dispatch")
                    from app.features.project_management.work_plans.execution import WorkPlanExecution
                    from app.features.project_management.work_plans.mirror_records import refresh_mirrors

                    await WorkPlanExecution.complete_plan(session, plan)
                    await refresh_mirrors(session, plan)
                elif pull.get("state") != "open":
                    await event(
                        session, row, "refused", "Original PR is closed without merge; reopen separately and refresh"
                    )
                elif not implemented and not stopped:
                    await event(
                        session,
                        row,
                        "reconciling",
                        "Prior delivery is not definitively stopped; inspect existing execution",
                    )
                elif (
                    await PipelineRunRepository().get_active_for_pull(session, project.id, run.pull_number) is not None
                ):
                    await event(session, row, "refused", "Another active Run owns the PR; no delivery dispatched")
                elif hold := await self.admission_hold(session, project, plan, item, run):
                    await event(
                        session,
                        row,
                        "awaiting-admission",
                        hold,
                    )
                else:
                    try:
                        await activate_recovery(session, run, item, row, pull, implemented=implemented, stopped=stopped)
                    except ProjectError as exc:
                        await event(session, row, "refused", str(exc))
                    else:
                        await event(
                            session,
                            row,
                            "running",
                            "Original Run resumed; prior budgets and successful Items retained",
                            {"head_sha": pull["head"]["sha"], "implemented": implemented},
                        )
                item.lease_token = item.lease_expires_at = None
                item.next_action_at = (
                    None
                    if not run and row.state == "awaiting-admission"
                    else get_current_utc_time() + timedelta(seconds=60)
                )
        except IntegrityError:
            async with AsyncTransaction() as session:
                locked = await self.locked(session, project_id, recovery_id)
                if locked and self.owns(locked[3], locked[4], token, generation):
                    await event(session, locked[4], "refused", "Another active Run owns the PR; no delivery dispatched")
                    locked[3].lease_token = locked[3].lease_expires_at = None

    @staticmethod
    def valid_pull(plan, item, run, pull):
        return (
            pull.get("number") == run.pull_number
            and pull.get("head", {}).get("ref") == item.branch
            and pull.get("base", {}).get("ref") == plan.base_branch
            and str((pull.get("base", {}).get("repo") or {}).get("full_name", "")).lower() == plan.repository
            and str((pull.get("head", {}).get("repo") or {}).get("full_name", "")).lower() == plan.repository
        )

    @staticmethod
    async def admission_hold(session, project, plan, item, run):
        now = get_current_utc_time()
        if not project.enabled:
            return "Project disabled; enable it before admission"
        if plan.scheduled_at and as_utc(plan.scheduled_at) > now:
            return f"Scheduled until {as_utc(plan.scheduled_at).isoformat()}"
        parents = await session.scalars(
            select(WorkPlan.state)
            .join(PlanDependency, PlanDependency.depends_on_id == WorkPlan.id)
            .where(PlanDependency.plan_id == plan.id)
        )
        dependencies = await session.scalars(
            select(WorkItem.state)
            .join(ItemDependency, ItemDependency.depends_on_id == WorkItem.id)
            .where(ItemDependency.item_id == item.id)
        )
        if any(p != "completed" for p in parents):
            return "Waiting for predecessor Plans to complete"
        if any(p != "succeeded" for p in dependencies):
            return "Waiting for predecessor Work Items to merge"
        catalog = await run_catalog(session, project, run)
        catalog = await session.get(AICatalog, catalog.id, with_for_update=True)
        if not await session.scalar(
            select(AICatalog.id).where(AICatalog.id == catalog.id, AICatalogRepository.admits_dispatch(now))
        ):
            return "AI catalog disabled or held by quota; inspect catalog availability"
        active = await AICatalogRepository().active_dispatch_count(session, catalog.id)
        queued = await session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.ai_catalog_id == catalog.id,
                PipelineRun.state.in_(("queued", "dispatching")),
                ~AICatalogRepository.run_holds_capacity(),
            )
        )
        count = active + (queued or 0)
        preparing = await session.scalar(
            select(func.count())
            .select_from(WorkItem)
            .where(WorkItem.ai_catalog_id == catalog.id, WorkItem.state == "preparing")
        )
        project_count = await session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.project_id == project.id,
                PipelineRun.state.in_(("queued", "dispatching", "implementing", "awaiting_ci")),
            )
        )
        project_preparing = await session.scalar(
            select(func.count())
            .select_from(WorkItem)
            .join(WorkPlan)
            .where(WorkPlan.project_id == project.id, WorkItem.state == "preparing")
        )
        limit = project.automation.get("max_in_flight_runs")
        if (count or 0) + (preparing or 0) >= AICatalogService.effective_concurrency(catalog) or (
            limit is not None and (project_count or 0) + (project_preparing or 0) >= limit
        ):
            return "Waiting for project or AI catalog capacity"
        run.ai_catalog_id, run.project_revision = catalog.id, project.revision
        return None
