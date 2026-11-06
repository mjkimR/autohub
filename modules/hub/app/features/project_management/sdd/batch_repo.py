from sqlalchemy import select

from .batch_models import SddActivityClaim, SddBatch, SddBatchControl, SddBatchMember


class BatchRepository:
    async def get(self, session, project_id, batch_id, *, lock=False):
        stmt = select(SddBatch).where(SddBatch.id == batch_id, SddBatch.project_id == project_id)
        return await session.scalar(stmt.with_for_update() if lock else stmt)

    async def request(self, session, project_id, request_id):
        return await session.scalar(
            select(SddBatch).where(SddBatch.project_id == project_id, SddBatch.request_id == request_id)
        )

    async def active(self, session, project_id):
        return await session.scalar(select(SddBatch).where(SddBatch.project_id == project_id, SddBatch.exclusion))

    async def members(self, session, batch_id):
        return list(
            await session.scalars(
                select(SddBatchMember).where(SddBatchMember.batch_id == batch_id).order_by(SddBatchMember.position)
            )
        )

    async def lists(self, session, project_id):
        return list(
            await session.scalars(
                select(SddBatch)
                .where(SddBatch.project_id == project_id)
                .order_by(SddBatch.created_at.desc(), SddBatch.id.desc())
                .limit(50)
            )
        )

    async def receipt(self, session, batch_id, request_id):
        return await session.scalar(
            select(SddBatchControl).where(
                SddBatchControl.batch_id == batch_id, SddBatchControl.request_id == request_id
            )
        )

    async def claims(self, session, member_id):
        return list(
            await session.scalars(
                select(SddActivityClaim)
                .where(SddActivityClaim.member_id == member_id)
                .order_by(SddActivityClaim.created_at)
            )
        )

    async def claim_request(self, session, project_id, request_id):
        return await session.scalar(
            select(SddActivityClaim).where(
                SddActivityClaim.project_id == project_id, SddActivityClaim.request_id == request_id
            )
        )

    async def claim_active(self, session, project_id, unit, activity):
        return await session.scalar(
            select(SddActivityClaim).where(
                SddActivityClaim.project_id == project_id,
                SddActivityClaim.unit == unit,
                SddActivityClaim.activity == activity,
                ~SddActivityClaim.settled,
            )
        )

    async def save(self, session, row):
        session.add(row)
        await session.flush()
        return row
