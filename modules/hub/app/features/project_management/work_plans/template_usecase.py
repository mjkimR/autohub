from typing import Annotated

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.mirror_records import refresh_mirrors
from app.features.project_management.work_plans.template_models import TemplateRequest
from app.features.project_management.work_plans.template_schemas import TemplateList, TemplateOutcome
from app.features.project_management.work_plans.template_service import TemplateService
from app.features.project_management.work_plans.usecases import WorkPlanUseCase
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class TemplateUseCase:
    def __init__(self, service: Annotated[TemplateService, Depends()], owner: Annotated[WorkPlanUseCase, Depends()]):
        self.service, self.owner = service, owner

    async def outcome(self, session, project_id, operation, request_id, receipt=None):
        if receipt is None:
            receipt = await self.service.repo.request(session, project_id, operation, request_id)
        if receipt is None:
            return TemplateOutcome(record_state="unknown", operation=operation, request_id=request_id)
        row = await self.service.get(session, project_id, receipt.template_id, deleted=True)
        result = TemplateOutcome.model_validate(
            {
                "record_state": "recorded",
                "operation": operation,
                "request_id": request_id,
                **receipt.result,
                "current_template": self.service.read(row),
            }
        )
        if receipt.plan_id:
            plan = await self.service.owner.get(session, project_id, receipt.plan_id)
            result.current_plan = await self.owner.read(session, plan)
        return result

    async def list(self, project_id, offset, limit):
        async with AsyncTransaction() as session:
            await self.service.owner.projects.get(session, project_id)
            rows, total = await self.service.repo.list(session, project_id, offset, limit)
            return TemplateList(items=[self.service.read(row) for row in rows], total_count=total)

    async def get(self, project_id, template_id):
        async with AsyncTransaction() as session:
            await self.service.owner.projects.get(session, project_id)
            return self.service.read(await self.service.get(session, project_id, template_id))

    async def read_request(self, project_id, operation, request_id):
        async with AsyncTransaction() as session:
            await self.service.owner.projects.get(session, project_id)
            return await self.outcome(session, project_id, operation, request_id)

    async def mutate(self, project_id, operation, target_id, data, actor):
        async with AsyncTransaction() as session:
            receipt = await self.service.mutate(session, project_id, operation, target_id, data, actor)
            return await self.outcome(session, project_id, operation, data.request_id, receipt)

    async def register(self, project_id, template_id, data, actor):
        fresh = False
        async with AsyncTransaction() as session:
            project = await self.service.owner.projects.get(session, project_id, lock=True)
            digest = request_digest({"target": str(template_id), "payload": data.model_dump(mode="json")})
            receipt = await self.service.replay(session, project_id, "register", data.request_id, actor, digest)
            if receipt is None:
                if await self.service.owner.repo.by_request(session, project_id, data.request_id):
                    raise ProjectError(
                        409, "Request belongs to ordinary registration", code="TEMPLATE_REQUEST_CONFLICT"
                    )
                row = await self.service.get(session, project_id, template_id, lock=True)
                if row.revision != data.template_revision or request_digest(row.definition) != data.template_digest:
                    raise ProjectError(409, "Template changed; reload for review", code="TEMPLATE_REVISION_CHANGED")
                if (
                    project.github_repository != data.expected_repository
                    or project.github_connector_id != data.expected_connector_id
                ):
                    raise ProjectError(
                        409, "Project binding changed; review current connection", code="TEMPLATE_BINDING_CHANGED"
                    )
                plan = await self.service.owner.create(session, project_id, data.payload, actor)
                await refresh_mirrors(session, plan)
                original_plan = await self.owner.read(session, plan)
                receipt = TemplateRequest(
                    project_id=project_id,
                    operation="register",
                    request_id=data.request_id,
                    actor=actor,
                    digest=digest,
                    template_id=row.id,
                    plan_id=plan.id,
                    result={
                        "original_template": self.service.read(row).model_dump(mode="json"),
                        "original_plan": original_plan.model_dump(mode="json"),
                        "reviewed_payload": data.payload.model_dump(mode="json"),
                        "repository": data.expected_repository,
                        "connector_id": str(data.expected_connector_id),
                    },
                )
                session.add(receipt)
                await session.flush()
                fresh = plan.state == "active"
            result = await self.outcome(session, project_id, "register", data.request_id, receipt)
        if fresh:
            try:
                await self.owner.kick.run(project_id)
                result = await self.read_request(project_id, "register", data.request_id)
            except Exception:
                result.refresh_error = "Plan registered; current admission or state refresh unavailable"
        return result
