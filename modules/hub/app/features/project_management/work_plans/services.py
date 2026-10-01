from typing import Annotated
from uuid import UUID, uuid4

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.work_plans.activity import record_change, snapshot
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app.features.project_management.work_plans.repos import WorkPlanRepository
from app.features.project_management.work_plans.schemas import (
    PlanControl,
    WorkPlanCreate,
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

    async def create(
        self, session: AsyncSession, project_id: UUID, data: WorkPlanWrite, actor: str = "system"
    ) -> WorkPlan:
        project = await self.projects.get(session, project_id, lock=True)
        request_id = data.request_id if isinstance(data, WorkPlanCreate) else None
        content = data.model_dump(mode="json", exclude={"request_id"})
        initial_state = data.state if isinstance(data, WorkPlanCreate) else "active"
        if initial_state == "active":
            content.pop("state", None)
        if initial_state != "draft":
            self.require_ready(data)
        # Preserve registration digests created before optional scheduling existed.
        if data.scheduled_at is None:
            content.pop("scheduled_at")
        content["depends_on"] = sorted(content["depends_on"])
        content["items"] = sorted(content["items"], key=lambda item: item["key"])
        for item in content["items"]:
            item["depends_on"] = sorted(item["depends_on"])
        digest = request_digest(content)
        existing = await self.repo.by_request(session, project_id, request_id) if request_id else None
        if existing:
            if existing.registration_digest != digest:
                raise ProjectError(
                    409,
                    "Registration request ID was already used for different work; recover the original plan before registering another request",
                )
            return existing
        if not project.github_repository or not project.github_connector_id:
            raise ProjectError(422, "Connect a GitHub repository before adding work plans")
        plan_id = uuid4()
        await self.validate_parents(session, project_id, plan_id, data.depends_on)
        plan = WorkPlan(
            id=plan_id,
            registration_request_id=request_id,
            registration_digest=digest if request_id else None,
            project_id=project_id,
            title=data.title,
            description=data.description,
            base_branch=data.base_branch,
            scheduled_at=data.scheduled_at,
            state=initial_state,
            repository=project.github_repository,
            connector_id=project.github_connector_id,
        )
        session.add(plan)
        await session.flush()
        items = [WorkItem(plan_id=plan.id, **item.model_dump(exclude={"depends_on"})) for item in data.items]
        session.add_all(items)
        await session.flush()
        await self.repo.replace_edges(session, plan, data.depends_on, items, data.items)
        await record_change(session, plan, {}, "created", actor)
        return plan

    async def validate_parents(self, session, project_id, plan_id, parents):
        graph = await self.repo.plan_graph(session, project_id)
        graph[plan_id] = parents
        try:
            validate_graph(graph)
        except ValueError as exc:
            raise ProjectError(422, str(exc)) from None

    async def update(
        self, session: AsyncSession, project_id: UUID, plan_id: UUID, data: WorkPlanUpdate, actor: str = "system"
    ) -> WorkPlan:
        await self.projects.get(session, project_id, lock=True)
        plan = await self.get(session, project_id, plan_id, lock=True)
        self.check_revision(plan, data.expected_revision)
        items = await self.repo.items(session, plan.id)
        if plan.state not in ("draft", "proposed", "active", "paused") or any(item.started_at for item in items):
            raise ProjectError(409, "Only plans with no started work can be edited")
        flexible = plan.state in ("draft", "proposed")
        if not flexible:
            self.require_ready(data)
        if not flexible and {item.key for item in items} != {item.key for item in data.items}:
            raise ProjectError(422, "Item keys are permanent; create another plan to add or remove work")
        await self.validate_parents(session, project_id, plan_id, data.depends_on)
        before = await snapshot(session, plan)
        if flexible:
            items = await self.repo.reconcile_items(session, plan, items, data.items)
            plan.state = "draft"
        plan.title, plan.description, plan.base_branch = data.title, data.description, data.base_branch
        plan.scheduled_at = data.scheduled_at
        by_key = {item.key: item for item in items}
        for write in data.items:
            row = by_key[write.key]
            row.title, row.description, row.acceptance = write.title, write.description, write.acceptance
        await self.repo.replace_edges(session, plan, data.depends_on, items, data.items)
        plan.revision += 1
        await record_change(session, plan, before, "updated", actor, data.reason)
        return plan

    async def control(
        self, session: AsyncSession, project_id: UUID, plan_id: UUID, data: PlanControl, actor: str = "system"
    ) -> WorkPlan:
        project = await self.projects.get(session, project_id, lock=True)
        plan = await self.get(session, project_id, plan_id, lock=True)
        self.check_revision(plan, data.expected_revision)
        if plan.state in ("completed", "revoked"):
            raise ProjectError(409, "Completed or revoked plans cannot be controlled")
        allowed = {
            "draft": {"propose", "ready", "resume", "revoke"},
            "proposed": {"draft", "ready", "resume", "revoke"},
            "paused": {"pause", "resume", "revoke"},
            "active": {"pause", "resume", "revoke"},
        }
        if data.action not in allowed.get(plan.state, set()):
            raise ProjectError(409, f"Cannot {data.action} a {plan.state} plan")
        before = await snapshot(session, plan)
        if data.action in ("propose", "ready", "resume"):
            if (plan.repository, plan.connector_id) != (project.github_repository, project.github_connector_id):
                raise ProjectError(409, "Repository connection changed; restore it or register a new plan")
            self.require_ready(WorkPlanWrite.model_validate({k: v for k, v in before.items() if k != "state"}))
            await self.validate_parents(
                session,
                project_id,
                plan_id,
                [UUID(value) for value in before["depends_on"]],
            )
        plan.state = {
            "pause": "paused",
            "resume": "active",
            "revoke": "revoked",
            "propose": "proposed",
            "draft": "draft",
            "ready": "paused",
        }[data.action]
        plan.revision += 1
        if data.action == "revoke":
            for item in await self.repo.items(session, plan.id):
                if item.started_at is None:
                    item.state, item.detail = "revoked", "Unstarted work was revoked"
        await session.flush()
        await record_change(session, plan, before, "control", actor, data.reason)
        return plan

    @staticmethod
    def require_ready(data: WorkPlanWrite) -> None:
        try:
            data.require_ready()
        except ValueError as exc:
            raise ProjectError(422, str(exc)) from None

    @staticmethod
    def check_revision(plan: WorkPlan, expected: int) -> None:
        if plan.revision != expected:
            raise ProjectError(409, "Work plan changed; reload before modifying it")
