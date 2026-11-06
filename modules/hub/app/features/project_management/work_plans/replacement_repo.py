"""Replacement owner queries. The use case owns Project serialization and transactions."""

from app.features.project_management.work_plans.replacement_models import (
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementLink,
    ReplacementReceipt,
)
from sqlalchemy import func, or_, select


async def links(session, item_id, offset=0, limit=10):
    own = ReplacementLink.original_item_id == item_id
    active = list(await session.scalars(select(ReplacementLink).where(own, ReplacementLink.active.is_(True))))
    query = select(ReplacementLink).where(own, ReplacementLink.active.is_(False))
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    history = list(
        await session.scalars(
            query.order_by(ReplacementLink.created_at.desc(), ReplacementLink.id.desc()).offset(offset).limit(limit)
        )
    )
    return active + history, total


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


async def acceptances(session, link_id, event_ids=None):
    query = select(ReplacementAcceptance).where(ReplacementAcceptance.link_id == link_id)
    if event_ids is not None:
        query = query.where(
            or_(
                ReplacementAcceptance.active.is_(True),
                ReplacementAcceptance.consumed.is_(True),
                ReplacementAcceptance.id.in_(event_ids),
            )
        )
    return list(await session.scalars(query.order_by(ReplacementAcceptance.created_at, ReplacementAcceptance.id)))


async def events(session, link_id, offset=0, limit=20):
    query = select(ReplacementEvent).where(ReplacementEvent.link_id == link_id)
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        await session.scalars(
            query.order_by(ReplacementEvent.revision, ReplacementEvent.id).offset(offset).limit(limit)
        )
    )
    return rows, total
