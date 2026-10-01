from typing import Annotated
from uuid import UUID

from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.activity import WorkPlanActivityRepository
from app.features.project_management.work_plans.activity_schemas import PlanActivityList, PlanActivityRead, PlanComment
from app.features.project_management.work_plans.kick import WorkPlanKick
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
    def __init__(
        self,
        service: Annotated[WorkPlanService, Depends()],
        kick: Annotated[WorkPlanKick, Depends()],
    ):
        self.service, self.kick = service, kick

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

    async def list(self, project_id: UUID, offset: int, limit: int, state: str | None = None) -> WorkPlanList:
        async with AsyncTransaction() as session:
            await self.service.projects.get(session, project_id)
            rows, total = await self.service.repo.list_for_project(session, project_id, offset, limit, state)
            return WorkPlanList(items=[await self.read(session, row) for row in rows], total_count=total)

    async def get(self, project_id: UUID, plan_id: UUID) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            return await self.read(session, await self.service.get(session, project_id, plan_id))

    async def by_request(self, project_id: UUID, request_id: UUID) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            await self.service.projects.get(session, project_id)
            plan = await self.service.repo.by_request(session, project_id, request_id)
            if plan is None:
                raise ProjectError(404, "No plan registered with this request ID")
            return await self.read(session, plan)

    async def create(self, project_id: UUID, data: WorkPlanWrite, actor: str = "system") -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.create(session, project_id, data, actor)
            await refresh_mirrors(session, plan)
            plan_id = plan.id
            if plan.state != "active":
                return await self.read(session, plan)
        return await self._started(project_id, plan_id)

    async def update(
        self, project_id: UUID, plan_id: UUID, data: WorkPlanUpdate, actor: str = "system"
    ) -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.update(session, project_id, plan_id, data, actor)
            await refresh_mirrors(session, plan)
            if plan.state != "active":
                return await self.read(session, plan)
        return await self._started(project_id, plan_id)

    async def control(self, project_id: UUID, plan_id: UUID, data: PlanControl, actor: str = "system") -> WorkPlanRead:
        async with AsyncTransaction() as session:
            plan = await self.service.control(session, project_id, plan_id, data, actor)
            await refresh_mirrors(session, plan)
            if data.action != "resume":
                return await self.read(session, plan)
        return await self._started(project_id, plan_id)

    async def _started(self, project_id: UUID, plan_id: UUID) -> WorkPlanRead:
        """After the change commits, start newly ready items now and answer with their state."""
        await self.kick.run(project_id)
        return await self.get(project_id, plan_id)

    async def activity(
        self, project_id: UUID, plan_id: UUID, offset: int = 0, limit: int = 50, comments_only: bool = False
    ) -> PlanActivityList:
        async with AsyncTransaction() as session:
            await self.service.get(session, project_id, plan_id)
            return await WorkPlanActivityRepository().list(session, plan_id, offset, limit, comments_only)

    async def comment(self, project_id: UUID, plan_id: UUID, data: PlanComment, actor: str) -> PlanActivityRead:
        async with AsyncTransaction() as session:
            plan = await self.service.get(session, project_id, plan_id, lock=True)
            return await WorkPlanActivityRepository().comment(session, plan, data, actor)
