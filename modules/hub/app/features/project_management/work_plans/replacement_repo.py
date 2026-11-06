"""Replacement owner queries. The use case owns Project serialization and transactions."""

from app.features.project_management.work_plans.replacement_models import (
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementLink,
    ReplacementReceipt,
)
from sqlalchemy import or_, select


async def links(session, item_id):
    return list(
        await session.scalars(
            select(ReplacementLink)
            .where(ReplacementLink.original_item_id == item_id)
            .order_by(ReplacementLink.created_at, ReplacementLink.id)
        )
    )


async def endpoint_links(session, ids, *, active=False):
    query = select(ReplacementLink).where(
        or_(ReplacementLink.original_item_id.in_(ids), ReplacementLink.replacement_item_id.in_(ids))
    )
    if active:
        query = query.where(ReplacementLink.active.is_(True))
    return list(await session.scalars(query))


async def receipt(session, project_id, operation, request_id):
    return await session.scalar(
        select(ReplacementReceipt).where(
            ReplacementReceipt.project_id == project_id,
            ReplacementReceipt.operation == operation,
            ReplacementReceipt.request_id == request_id,
        )
    )


async def acceptances(session, link_id):
    return list(
        await session.scalars(
            select(ReplacementAcceptance)
            .where(ReplacementAcceptance.link_id == link_id)
            .order_by(ReplacementAcceptance.created_at, ReplacementAcceptance.id)
        )
    )


async def events(session, link_id):
    return list(
        await session.scalars(
            select(ReplacementEvent)
            .where(ReplacementEvent.link_id == link_id)
            .order_by(ReplacementEvent.created_at, ReplacementEvent.id)
        )
    )
