from uuid import UUID

from app.features.project_management.work_plans.grouping import normalize_group_key
from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkItem, WorkPlan
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class WorkPlanRepository:
    async def get(self, session: AsyncSession, plan_id: UUID, *, lock: bool = False) -> WorkPlan | None:
        return await session.get(WorkPlan, plan_id, with_for_update=lock)

    async def by_request(self, session: AsyncSession, project_id: UUID, request_id: UUID) -> WorkPlan | None:
        return await session.scalar(
            select(WorkPlan).where(WorkPlan.project_id == project_id, WorkPlan.registration_request_id == request_id)
        )

    async def items(self, session: AsyncSession, plan_id: UUID) -> list[WorkItem]:
        return list(await session.scalars(select(WorkItem).where(WorkItem.plan_id == plan_id).order_by(WorkItem.key)))

    async def list_for_project(
        self,
        session: AsyncSession,
        project_id: UUID,
        offset=0,
        limit=50,
        state: str | None = None,
        group_key: str | None = None,
    ):
        conditions = [WorkPlan.project_id == project_id]
        if state:
            conditions.append(WorkPlan.state == state)
        if group_key is not None:
            conditions.append(WorkPlan.group_key == normalize_group_key(group_key))
        query = select(WorkPlan).where(*conditions)
        rows = await session.scalars(
            query.order_by(WorkPlan.created_at.desc(), WorkPlan.id).offset(offset).limit(limit)
        )
        count = await session.scalar(select(func.count()).select_from(WorkPlan).where(*conditions))
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

    async def reconcile_items(self, session, plan, items, writes):
        await session.execute(delete(ItemDependency).where(ItemDependency.plan_id == plan.id))
        wanted = {write.key for write in writes}
        retained = {item.key: item for item in items if item.key in wanted}
        for item in items:
            if item.key not in wanted:
                await session.delete(item)
        for write in writes:
            if write.key not in retained:
                row = WorkItem(plan_id=plan.id, **write.model_dump(exclude={"depends_on"}))
                session.add(row)
                retained[write.key] = row
        await session.flush()
        return list(retained.values())
