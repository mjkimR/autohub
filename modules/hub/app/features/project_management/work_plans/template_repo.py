from uuid import UUID

from app.features.project_management.work_plans.template_models import TemplateRequest, WorkPlanTemplate
from sqlalchemy import func, select


class TemplateRepository:
    async def get(self, session, project_id: UUID, template_id: UUID, *, lock=False):
        query = select(WorkPlanTemplate).where(
            WorkPlanTemplate.id == template_id, WorkPlanTemplate.project_id == project_id
        )
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return await session.scalar(query)

    async def request(self, session, project_id, operation, request_id):
        return await session.scalar(
            select(TemplateRequest).where(
                TemplateRequest.project_id == project_id,
                TemplateRequest.operation == operation,
                TemplateRequest.request_id == request_id,
            )
        )

    async def list(self, session, project_id, offset, limit):
        where = (WorkPlanTemplate.project_id == project_id, WorkPlanTemplate.deleted.is_(False))
        rows = list(
            await session.scalars(
                select(WorkPlanTemplate)
                .where(*where)
                .order_by(WorkPlanTemplate.name, WorkPlanTemplate.id)
                .offset(offset)
                .limit(limit)
            )
        )
        total = await session.scalar(select(func.count()).select_from(WorkPlanTemplate).where(*where))
        return rows, total or 0
