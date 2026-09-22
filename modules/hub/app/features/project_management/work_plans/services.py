from typing import Annotated
from uuid import UUID, uuid4

from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanUpdate,
    WorkPlanWrite,
    validate_graph,
)
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


class WorkPlanService:
    def __init__(self, repo: Annotated[WorkPlanRepository, Depends()], projects: Annotated[ProjectService, Depends()]):
        self.repo, self.projects = repo, projects

    async def get(self, session: AsyncSession, project_id: UUID, plan_id: UUID, *, lock=False) -> WorkPlan:
        plan = await self.repo.get(session, plan_id, lock=lock)
        if plan is None or plan.project_id != project_id:
            raise ProjectError(404, "Work plan not found")
        return plan

    async def create(self, session: AsyncSession, project_id: UUID, data: WorkPlanWrite) -> WorkPlan:
        project = await self.projects.get(session, project_id, lock=True)
        if not project.github_repository or not project.github_connector_id:
            raise ProjectError(422, "Connect a GitHub repository before adding work plans")
        plan_id = uuid4()
        await self.validate_parents(session, project_id, plan_id, data.depends_on)
        plan = WorkPlan(
            id=plan_id,
            project_id=project_id,
            title=data.title,
            description=data.description,
            base_branch=data.base_branch,
            repository=project.github_repository,
            connector_id=project.github_connector_id,
        )
        session.add(plan)
        await session.flush()
        items = [WorkItem(plan_id=plan.id, **item.model_dump(exclude={"depends_on"})) for item in data.items]
        session.add_all(items)
        await session.flush()
        await self.repo.replace_edges(session, plan, data.depends_on, items, data.items)
        return plan

    async def validate_parents(self, session, project_id, plan_id, parents):
        graph = await self.repo.plan_graph(session, project_id)
        graph[plan_id] = parents
        try:
            validate_graph(graph)
        except ValueError as exc:
            raise ProjectError(422, str(exc)) from None

    async def update(self, session: AsyncSession, project_id: UUID, plan_id: UUID, data: WorkPlanUpdate) -> WorkPlan:
        await self.projects.get(session, project_id, lock=True)
        plan = await self.get(session, project_id, plan_id, lock=True)
        self.check_revision(plan, data.expected_revision)
        items = await self.repo.items(session, plan.id)
        if plan.state not in ("active", "paused") or any(item.started_at for item in items):
            raise ProjectError(409, "Only plans with no started work can be edited")
        if {item.key for item in items} != {item.key for item in data.items}:
            raise ProjectError(422, "Item keys are permanent; create another plan to add or remove work")
        await self.validate_parents(session, project_id, plan_id, data.depends_on)
        plan.title, plan.description, plan.base_branch = data.title, data.description, data.base_branch
        by_key = {item.key: item for item in items}
        for write in data.items:
            row = by_key[write.key]
            row.title, row.description, row.acceptance = write.title, write.description, write.acceptance
        await self.repo.replace_edges(session, plan, data.depends_on, items, data.items)
        plan.revision += 1
        return plan

    async def control(self, session: AsyncSession, project_id: UUID, plan_id: UUID, data: PlanControl) -> WorkPlan:
        await self.projects.get(session, project_id, lock=True)
        plan = await self.get(session, project_id, plan_id, lock=True)
        self.check_revision(plan, data.expected_revision)
        if plan.state in ("completed", "revoked"):
            raise ProjectError(409, "Completed or revoked plans cannot be controlled")
        plan.state = {"pause": "paused", "resume": "active", "revoke": "revoked"}[data.action]
        plan.revision += 1
        if data.action == "revoke":
            for item in await self.repo.items(session, plan.id):
                if item.started_at is None:
                    item.state, item.detail = "revoked", "Unstarted work was revoked"
        await session.flush()
        return plan

    @staticmethod
    def check_revision(plan: WorkPlan, expected: int) -> None:
        if plan.revision != expected:
            raise ProjectError(409, "Work plan changed; reload before modifying it")
