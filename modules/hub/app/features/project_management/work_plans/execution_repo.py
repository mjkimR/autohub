"""Atomic admission and fenced observation of work items."""

from datetime import timedelta
from uuid import UUID, uuid4

from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.models import PipelineRun
from app.features.project_management.pipeline_runs.usecases.catalogs import project_catalog
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkItem, WorkPlan
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import and_, case, exists, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased


class WorkExecutionRepository:
    async def claim(
        self, session: AsyncSession, project_id: UUID, *, phase: str = "any"
    ) -> tuple[WorkPlan, WorkItem] | None:
        project = await ProjectRepository().get(session, project_id, lock=True)
        if project is None:
            return None
        now = get_current_utc_time()
        parent_plan, parent_item = aliased(WorkPlan), aliased(WorkItem)
        plan_wait = exists(
            select(PlanDependency.plan_id)
            .join(parent_plan, parent_plan.id == PlanDependency.depends_on_id)
            .where(PlanDependency.plan_id == WorkPlan.id, parent_plan.state != "completed")
        )
        item_wait = exists(
            select(ItemDependency.item_id)
            .join(parent_item, parent_item.id == ItemDependency.depends_on_id)
            .where(ItemDependency.item_id == WorkItem.id, parent_item.state != "succeeded")
        )
        waiting_ready = (
            and_(
                WorkItem.state == "waiting",
                WorkPlan.state == "active",
                ~plan_wait,
                ~item_wait,
                WorkPlan.repository == project.github_repository,
                WorkPlan.connector_id == project.github_connector_id,
            )
            if project.enabled
            else WorkItem.id.is_(None)
        )
        candidate = await session.scalar(
            select(WorkItem)
            .join(WorkPlan, WorkPlan.id == WorkItem.plan_id)
            .where(
                WorkPlan.project_id == project_id,
                WorkItem.started_at.is_not(None)
                if phase == "observe"
                else waiting_ready
                if phase == "admit"
                else true(),
                or_(
                    waiting_ready,
                    and_(
                        WorkItem.started_at.is_not(None),
                        WorkItem.state.not_in(("succeeded", "revoked", "preparation_failed")),
                    ),
                ),
                or_(WorkItem.next_action_at.is_(None), WorkItem.next_action_at <= now),
                or_(WorkItem.lease_expires_at.is_(None), WorkItem.lease_expires_at <= now),
            )
            .order_by(
                case((WorkItem.started_at.is_not(None), 0), else_=1),
                WorkItem.next_action_at.nullsfirst(),
                WorkItem.created_at,
                WorkItem.id,
            )
            .limit(1)
        )
        if candidate is None:
            return None
        plan = await session.get(WorkPlan, candidate.plan_id, with_for_update=True)
        assert plan is not None
        if candidate.state == "waiting":
            catalog = await project_catalog(session, project)
            catalog = await AICatalogRepository().get(session, catalog.id, lock=True)
            assert catalog is not None
            admission = await session.scalar(
                select(catalog.__class__.id).where(
                    catalog.__class__.id == catalog.id,
                    AICatalogRepository.admits_dispatch(now),
                )
            )
            active = await AICatalogRepository().active_dispatch_count(session, catalog.id)
            # Reserve waiting dispatches too, without recounting admitted ones in active.
            queued = (
                await session.scalar(
                    select(func.count())
                    .select_from(PipelineRun)
                    .where(
                        PipelineRun.ai_catalog_id == catalog.id,
                        PipelineRun.state.in_(("queued", "dispatching")),
                        ~AICatalogRepository.run_holds_capacity(),
                    )
                )
                or 0
            )
            preparing = (
                await session.scalar(
                    select(func.count())
                    .select_from(WorkItem)
                    .where(
                        WorkItem.ai_catalog_id == catalog.id,
                        WorkItem.state == "preparing",
                    )
                )
                or 0
            )
            started = (
                await session.scalar(
                    select(func.count())
                    .select_from(PipelineRun)
                    .where(
                        PipelineRun.project_id == project_id,
                        PipelineRun.state.in_(("queued", "dispatching", "implementing", "awaiting_ci")),
                    )
                )
                or 0
            )
            project_preparing = (
                await session.scalar(
                    select(func.count())
                    .select_from(WorkItem)
                    .join(WorkPlan)
                    .where(
                        WorkPlan.project_id == project_id,
                        WorkItem.state == "preparing",
                    )
                )
                or 0
            )
            limit = project.automation.get("max_in_flight_runs")
            if (
                admission is None
                or active + queued + preparing >= AICatalogService.effective_concurrency(catalog)
                or (limit is not None and started + project_preparing >= limit)
            ):
                candidate.detail = "Waiting for project or AI catalog capacity"
                candidate.next_action_at = now + timedelta(seconds=60)
                return None
            candidate.state, candidate.started_at = "preparing", now
            candidate.ai_catalog_id = catalog.id
            candidate.branch = f"autohub/work/{candidate.id}"
            candidate.detail = None
        await session.flush()
        token = uuid4()
        # Conditional update also fences workers that selected the same row on a different project tick.
        row = (
            await session.execute(
                update(WorkItem)
                .where(
                    WorkItem.id == candidate.id,
                    or_(WorkItem.lease_expires_at.is_(None), WorkItem.lease_expires_at <= now),
                )
                .values(
                    lease_token=token,
                    lease_expires_at=now + timedelta(seconds=120),
                    next_action_at=now + timedelta(seconds=60),
                )
                .returning(WorkItem)
                .execution_options(populate_existing=True, synchronize_session="fetch")
            )
        ).scalar_one_or_none()
        return (plan, row) if row else None

    async def leased(self, session: AsyncSession, item_id: UUID, token: UUID | None) -> WorkItem | None:
        if token is None:
            return None
        return await session.scalar(
            select(WorkItem)
            .where(
                WorkItem.id == item_id,
                WorkItem.lease_token == token,
                WorkItem.lease_expires_at > get_current_utc_time(),
            )
            .with_for_update()
        )
