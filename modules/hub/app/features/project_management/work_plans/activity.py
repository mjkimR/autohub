"""Append-only Plan discussion and transactional specification history."""

from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.activity_schemas import PlanActivityList, PlanActivityRead
from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkPlanActivity
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.schemas import WorkItemWrite, WorkPlanWrite
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import func, select


async def snapshot(session, plan) -> dict:
    items = await WorkPlanRepository().items(session, plan.id)
    keys = {item.id: item.key for item in items}
    edges = list(await session.scalars(select(ItemDependency).where(ItemDependency.plan_id == plan.id)))
    parents = list(await session.scalars(select(PlanDependency.depends_on_id).where(PlanDependency.plan_id == plan.id)))
    data = WorkPlanWrite(
        title=plan.title,
        description=plan.description,
        base_branch=plan.base_branch,
        scheduled_at=as_utc(plan.scheduled_at) if plan.scheduled_at else None,
        depends_on=sorted(parents),
        items=[
            WorkItemWrite(
                key=item.key,
                title=item.title,
                description=item.description,
                acceptance=item.acceptance,
                depends_on=sorted(keys[edge.depends_on_id] for edge in edges if edge.item_id == item.id),
            )
            for item in items
        ],
    )
    return {**data.model_dump(mode="json"), "state": plan.state}


async def record_change(session, plan, before: dict, kind: str, actor: str, reason: str = "") -> None:
    after = await snapshot(session, plan)
    changes = {
        key: {"before": before.get(key), "after": value}
        for key, value in after.items()
        if key not in before or before[key] != value
    }
    if changes:
        session.add(
            WorkPlanActivity(
                plan_id=plan.id,
                kind=kind,
                actor=actor,
                revision=plan.revision,
                body=reason,
                changes=changes,
                created_at=get_current_utc_time(),
            )
        )
        await session.flush()


class WorkPlanActivityRepository:
    async def list(self, session, plan_id, offset, limit, comments_only) -> PlanActivityList:
        conditions = [WorkPlanActivity.plan_id == plan_id]
        if comments_only:
            conditions.append(WorkPlanActivity.kind == "comment")
        rows = await session.scalars(
            select(WorkPlanActivity)
            .where(*conditions)
            .order_by(WorkPlanActivity.created_at.desc(), WorkPlanActivity.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total = await session.scalar(select(func.count()).select_from(WorkPlanActivity).where(*conditions))
        return PlanActivityList(items=[PlanActivityRead.model_validate(row) for row in rows], total_count=total or 0)

    async def comment(self, session, plan, data, actor) -> PlanActivityRead:
        existing = await session.scalar(
            select(WorkPlanActivity).where(
                WorkPlanActivity.plan_id == plan.id, WorkPlanActivity.request_id == data.request_id
            )
        )
        if existing:
            if (existing.body, existing.actor) != (data.body, actor):
                raise ProjectError(409, "Comment request ID was already used for different content or author")
            return PlanActivityRead.model_validate(existing)
        row = WorkPlanActivity(
            plan_id=plan.id,
            request_id=data.request_id,
            kind="comment",
            actor=actor,
            revision=plan.revision,
            body=data.body,
            created_at=get_current_utc_time(),
            changes={},
        )
        session.add(row)
        await session.flush()
        return PlanActivityRead.model_validate(row)
