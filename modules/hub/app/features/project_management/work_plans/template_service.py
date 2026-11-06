from typing import Annotated
from uuid import uuid4

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.work_plans.models import ItemDependency
from app.features.project_management.work_plans.services import WorkPlanService
from app.features.project_management.work_plans.template_models import TemplateRequest, WorkPlanTemplate
from app.features.project_management.work_plans.template_repo import TemplateRepository
from app.features.project_management.work_plans.template_schemas import TemplateDefinition, WorkPlanTemplateRead
from fastapi import Depends
from sqlalchemy import select


class TemplateService:
    def __init__(self, repo: Annotated[TemplateRepository, Depends()], owner: Annotated[WorkPlanService, Depends()]):
        self.repo, self.owner = repo, owner

    def read(self, row):
        return WorkPlanTemplateRead(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            revision=row.revision,
            deleted=row.deleted,
            schema_version=row.schema_version,
            definition=row.definition,
            digest=request_digest(row.definition),
            created_actor=row.created_actor,
            updated_actor=row.updated_actor,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get(self, session, project_id, template_id, *, lock=False, deleted=False):
        row = await self.repo.get(session, project_id, template_id, lock=lock)
        if row is None or (row.deleted and not deleted):
            raise ProjectError(404, "Work Plan template unavailable", code="TEMPLATE_UNAVAILABLE")
        return row

    async def replay(self, session, project_id, operation, request_id, actor, digest):
        row = await self.repo.request(session, project_id, operation, request_id)
        if row is not None and (row.actor != actor or row.digest != digest):
            raise ProjectError(
                409,
                "Template request identity already used for another target, actor or payload",
                code="TEMPLATE_REQUEST_CONFLICT",
            )
        return row

    async def mutate(self, session, project_id, operation, target_id, data, actor):
        await self.owner.projects.get(session, project_id, lock=True)
        digest = request_digest(
            {"target": str(target_id) if target_id else None, "payload": data.model_dump(mode="json")}
        )
        old = await self.replay(session, project_id, operation, data.request_id, actor, digest)
        if old:
            return old
        source_id, source_revision = None, None
        omitted = []
        if operation == "from-plan":
            plan = await self.owner.get(session, project_id, data.source_plan_id, lock=True)
            if plan.revision != data.expected_revision:
                raise ProjectError(409, "Source Plan changed; reload for review", code="TEMPLATE_SOURCE_CHANGED")
            items = await self.owner.repo.items(session, plan.id)
            keys = {i.id: i.key for i in items}
            edges = list(await session.scalars(select(ItemDependency).where(ItemDependency.plan_id == plan.id)))
            definition = TemplateDefinition.model_validate(
                {
                    "title": plan.title,
                    "description": plan.description,
                    "base_branch": plan.base_branch,
                    "items": [
                        {
                            "key": i.key,
                            "title": i.title,
                            "description": i.description,
                            "acceptance": i.acceptance,
                            "depends_on": [keys[e.depends_on_id] for e in edges if e.item_id == i.id],
                        }
                        for i in items
                    ],
                }
            )
            source_id, source_revision = plan.id, plan.revision
            omitted = [
                "attachments",
                "execution and approval history",
                "PR/Issue identities",
                "schedule",
                "group",
                "external Plan dependencies",
            ]
        else:
            definition = data.definition if operation in ("create", "update") else None
        if operation in ("create", "from-plan"):
            assert definition is not None
            row = WorkPlanTemplate(
                id=uuid4(),
                project_id=project_id,
                name=data.name,
                definition=definition.model_dump(mode="json"),
                created_actor=actor,
                updated_actor=actor,
            )
            session.add(row)
        else:
            row = await self.get(session, project_id, target_id, lock=True)
            if row.revision != data.expected_revision:
                raise ProjectError(409, "Template changed; reload for review", code="TEMPLATE_REVISION_CHANGED")
            row.revision += 1
            row.updated_actor = actor
            if operation == "delete":
                row.deleted = True
            else:
                assert definition is not None
                row.name, row.definition = data.name, definition.model_dump(mode="json")
        await session.flush()
        await session.refresh(row)
        result = {
            "original_template": self.read(row).model_dump(mode="json"),
            "source_plan_id": str(source_id) if source_id else None,
            "source_revision": source_revision,
            "omitted": omitted,
        }
        receipt = TemplateRequest(
            project_id=project_id,
            operation=operation,
            request_id=data.request_id,
            actor=actor,
            digest=digest,
            template_id=row.id,
            plan_id=None,
            result=result,
        )
        session.add(receipt)
        await session.flush()
        return receipt
