"""Bulk reverse relationships for already-selected run pages."""

from app.features.ai_catalogs.models import AICatalogSession
from app.features.project_management.sdd.batch_models import SddActivityClaim, SddBatch, SddBatchMember
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from sqlalchemy import select


class RunOriginRepository:
    async def work_items(self, session, ids):
        return (
            await session.execute(
                select(WorkItem.pipeline_run_id, WorkItem.id, WorkPlan.id, WorkPlan.project_id)
                .join(WorkPlan, WorkPlan.id == WorkItem.plan_id)
                .where(WorkItem.pipeline_run_id.in_(ids))
            )
        ).all()

    async def sessions(self, session, ids):
        return (
            await session.execute(
                select(
                    AICatalogSession.pipeline_run_id,
                    AICatalogSession.id,
                    AICatalogSession.ai_catalog_id,
                    AICatalogSession.url,
                ).where(AICatalogSession.pipeline_run_id.in_(ids))
            )
        ).all()

    async def claims(self, session, ids):
        return (
            await session.execute(
                select(
                    SddActivityClaim.run_id,
                    SddActivityClaim.id,
                    SddActivityClaim.project_id,
                    SddActivityClaim.unit,
                    SddBatch.id,
                    SddBatch.project_id,
                )
                .outerjoin(SddBatchMember, SddBatchMember.id == SddActivityClaim.member_id)
                .outerjoin(SddBatch, SddBatch.id == SddBatchMember.batch_id)
                .where(SddActivityClaim.run_id.in_(ids))
            )
        ).all()
