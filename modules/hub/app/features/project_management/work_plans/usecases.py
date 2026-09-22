from typing import Annotated
from uuid import UUID

from app.features.project_management.work_plans.mirror_records import refresh_mirrors
from app.features.project_management.work_plans.models import ItemDependency, PlanDependency, WorkIssueMirror
from app.features.project_management.work_plans.schemas import (
    IssueMirrorRead,
    PlanControl,
    WorkItemRead,
    WorkPlanList,
    WorkPlanRead,
    WorkPlanUpdate,
    WorkPlanWrite,
)
from app.features.project_management.work_plans.services import WorkPlanService
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends
from sqlalchemy import select


class WorkPlanUseCase:
    def __init__(self, service: Annotated[WorkPlanService, Depends()]):
        self.service = service

    async def read(self, session, plan) -> WorkPlanRead:
        items = await self.service.repo.items(session, plan.id)
        keys = {item.id: item.key for item in items}
        edges = list(await session.scalars(select(ItemDependency).where(ItemDependency.plan_id == plan.id)))
        mirrors = {
            row.entity_id: row
            for row in await session.scalars(select(WorkIssueMirror).where(WorkIssueMirror.plan_id == plan.id))
        }

        def mirror(id):
            row = mirrors.get(id)
            return (
                None
                if row is None
                else IssueMirrorRead(
                    issue_url=row.issue_url,
                    error=row.error,
                    pending=row.synced_digest != row.digest,
                )
            )

        parents = list(
            await session.scalars(select(PlanDependency.depends_on_id).where(PlanDependency.plan_id == plan.id))
        )
        return WorkPlanRead.model_validate(plan).model_copy(
            update={
                "depends_on": parents,
                "issue": mirror(plan.id),
                "items": [
                    WorkItemRead.model_validate(item).model_copy(
                        update={
                            "depends_on": [keys[edge.depends_on_id] for edge in edges if edge.item_id == item.id],
                            "issue": mirror(item.id),
                        }
                    )
                    for item in items
                ],
            }
        )

    async def list(self, project_id: UUID, offset: int, limit: int) -> WorkPlanList:
        async with AsyncTransaction() as session:
            await self.service.projects.get(session, project_id)
            rows, total = await self.service.repo.list_for_project(session, project_id, offset, limit)
            return WorkPlanList(items=[await self.read(session, row) for row in rows], total_count=total)

    async def get(self, project_id: UUID, plan_id: UUID) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            return await self.read(session, await self.service.get(session, project_id, plan_id))

    async def create(self, project_id: UUID, data: WorkPlanWrite) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.create(session, project_id, data)
            await refresh_mirrors(session, plan)
            return await self.read(session, plan)

    async def update(self, project_id: UUID, plan_id: UUID, data: WorkPlanUpdate) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.update(session, project_id, plan_id, data)
            await refresh_mirrors(session, plan)
            return await self.read(session, plan)

    async def control(self, project_id: UUID, plan_id: UUID, data: PlanControl) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.control(session, project_id, plan_id, data)
            await refresh_mirrors(session, plan)
            return await self.read(session, plan)
