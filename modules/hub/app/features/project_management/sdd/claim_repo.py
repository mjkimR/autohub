from sqlalchemy import select

from .claim_models import SddActivityClaim


class ClaimRepository:
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

    async def claim(self, session, project_id, claim_id, *, lock=False):
        stmt = select(SddActivityClaim).where(
            SddActivityClaim.id == claim_id, SddActivityClaim.project_id == project_id
        )
        return await session.scalar(stmt.with_for_update() if lock else stmt)
