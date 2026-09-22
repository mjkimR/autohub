from uuid import UUID

from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkItem, WorkPlan
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class WorkPlanRepository:
    async def get(self, session: AsyncSession, plan_id: UUID, *, lock: bool = False) -> WorkPlan | None:
        return await session.get(WorkPlan, plan_id, with_for_update=lock)

    async def items(self, session: AsyncSession, plan_id: UUID) -> list[WorkItem]:
        return list(await session.scalars(select(WorkItem).where(WorkItem.plan_id == plan_id).order_by(WorkItem.key)))

    async def list_for_project(self, session: AsyncSession, project_id: UUID, offset=0, limit=50):
        query = select(WorkPlan).where(WorkPlan.project_id == project_id)
        rows = await session.scalars(
            query.order_by(WorkPlan.created_at.desc(), WorkPlan.id).offset(offset).limit(limit)
        )
        count = await session.scalar(
            select(func.count()).select_from(WorkPlan).where(WorkPlan.project_id == project_id)
        )
        return list(rows), count or 0

    async def plan_graph(self, session: AsyncSession, project_id: UUID) -> dict[UUID, list[UUID]]:
        ids = await session.scalars(select(WorkPlan.id).where(WorkPlan.project_id == project_id))
        graph: dict[UUID, list[UUID]] = {key: [] for key in ids}
        for edge in await session.scalars(select(PlanDependency).where(PlanDependency.project_id == project_id)):
            graph[edge.plan_id].append(edge.depends_on_id)
        return graph

    async def replace_edges(self, session: AsyncSession, plan: WorkPlan, parents: list[UUID], items, writes) -> None:
        await session.execute(delete(PlanDependency).where(PlanDependency.plan_id == plan.id))
        await session.execute(delete(ItemDependency).where(ItemDependency.plan_id == plan.id))
        for parent in parents:
            session.add(PlanDependency(project_id=plan.project_id, plan_id=plan.id, depends_on_id=parent))
        by_key = {item.key: item.id for item in items}
        for data in writes:
            for parent in data.depends_on:
                session.add(ItemDependency(plan_id=plan.id, item_id=by_key[data.key], depends_on_id=by_key[parent]))
        await session.flush()
