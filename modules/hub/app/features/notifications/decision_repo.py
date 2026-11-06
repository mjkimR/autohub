from datetime import datetime
from uuid import UUID

from app.features.notifications.decision_models import (
    DecisionNotice,
    DecisionNoticeAttempt,
    DecisionNoticeQueue,
    DecisionNoticeRequest,
    DecisionSubscription,
)
from app.features.notifications.models import NotificationChannel
from app.features.project_management.pipeline_runs.models import FINAL_RUN_STATES, DecisionEntry, PipelineRun
from app.features.project_management.projects.models import Project
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class DecisionNoticeRepository:
    async def channel(self, session, id):
        return await session.get(NotificationChannel, id, with_for_update=True, populate_existing=True)

    async def subscription(self, session, id):
        return await session.get(DecisionSubscription, id, populate_existing=True)

    async def request(self, session, channel_id, operation, request_id):
        return await session.scalar(
            select(DecisionNoticeRequest).where(
                DecisionNoticeRequest.channel_id == channel_id,
                DecisionNoticeRequest.operation == operation,
                DecisionNoticeRequest.request_id == request_id,
            )
        )

    async def projects_exist(self, session, ids):
        found = set(await session.scalars(select(Project.id).where(Project.id.in_(ids))))
        return found == set(ids)

    async def generations(self, session, channel_id, destination):
        return list(
            await session.scalars(
                select(DecisionNotice)
                .where(
                    DecisionNotice.channel_id == channel_id,
                    DecisionNotice.destination_generation == destination,
                    DecisionNotice.state == "pending",
                )
                .order_by(DecisionNotice.created_at, DecisionNotice.id)
                .limit(100)
            )
        )

    async def generation(self, session, channel_id, destination, key, fingerprint):
        return await session.scalar(
            select(DecisionNotice).where(
                DecisionNotice.channel_id == channel_id,
                DecisionNotice.destination_generation == destination,
                DecisionNotice.decision_key == key,
                DecisionNotice.fingerprint == fingerprint,
            )
        )

    async def notice(self, session, channel_id, id):
        return await session.scalar(
            select(DecisionNotice).where(DecisionNotice.id == id, DecisionNotice.channel_id == channel_id)
        )

    async def exact(self, session, key):
        return (
            await session.execute(
                select(DecisionEntry, PipelineRun, Project)
                .join(PipelineRun, PipelineRun.id == DecisionEntry.run_id)
                .join(Project, Project.id == DecisionEntry.project_id)
                .where(DecisionEntry.key == key, PipelineRun.state.not_in(FINAL_RUN_STATES))
            )
        ).first()

    async def scan(self, session, sub):
        q = (
            select(DecisionEntry, PipelineRun, Project)
            .join(PipelineRun, PipelineRun.id == DecisionEntry.run_id)
            .join(Project, Project.id == DecisionEntry.project_id)
            .where(PipelineRun.state.not_in(FINAL_RUN_STATES))
        )
        if sub.scan_time is not None:
            q = q.where(
                or_(
                    DecisionEntry.waiting_since > sub.scan_time,
                    and_(DecisionEntry.waiting_since == sub.scan_time, DecisionEntry.key > sub.scan_key),
                )
            )
        return list(
            (await session.execute(q.order_by(DecisionEntry.waiting_since, DecisionEntry.key).limit(100))).all()
        )

    async def expired(self, session, channel_id, now):
        return list(
            await session.scalars(
                select(DecisionNoticeAttempt).where(
                    DecisionNoticeAttempt.channel_id == channel_id,
                    DecisionNoticeAttempt.state == "sending",
                    DecisionNoticeAttempt.lease_expires_at <= now,
                )
            )
        )

    async def attempt(self, session, id):
        return await session.get(DecisionNoticeAttempt, id, populate_existing=True)

    async def history(self, session, channel_id, cursor, limit):
        q = select(DecisionNotice).where(DecisionNotice.channel_id == channel_id)
        if cursor:
            try:
                timestamp, id = cursor.split("|", 1)
                stamp, identity = datetime.fromisoformat(timestamp), UUID(id)
            except ValueError:
                from app.features.project_management.projects.errors import ProjectError

                raise ProjectError(422, "Invalid history cursor") from None
            q = q.where(
                or_(
                    DecisionNotice.created_at < stamp,
                    and_(DecisionNotice.created_at == stamp, DecisionNotice.id < identity),
                )
            )
        rows = list(
            await session.scalars(
                q.order_by(DecisionNotice.created_at.desc(), DecisionNotice.id.desc()).limit(limit + 1)
            )
        )
        attempts = list(
            await session.scalars(
                select(DecisionNoticeAttempt)
                .where(DecisionNoticeAttempt.channel_id == channel_id)
                .order_by(DecisionNoticeAttempt.created_at.desc(), DecisionNoticeAttempt.id.desc())
                .limit(100)
            )
        )
        return rows, attempts

    async def compact(self, session, channel_id):
        stale = list(
            await session.scalars(
                select(DecisionNoticeAttempt)
                .where(DecisionNoticeAttempt.channel_id == channel_id, DecisionNoticeAttempt.state != "sending")
                .order_by(DecisionNoticeAttempt.created_at.desc(), DecisionNoticeAttempt.id.desc())
                .offset(100)
                .limit(100)
            )
        )
        for row in stale:
            await session.delete(row)

    async def next_channels(self, session):
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(
            insert(DecisionNoticeQueue)
            .values(name="decision-notices", cursor="")
            .on_conflict_do_nothing(index_elements=["name"])
        )
        queue = await session.get(DecisionNoticeQueue, "decision-notices", with_for_update=True, populate_existing=True)
        pending_delivery = (
            select(DecisionNoticeAttempt.id)
            .where(
                DecisionNoticeAttempt.channel_id == DecisionSubscription.channel_id,
                DecisionNoticeAttempt.state == "sending",
            )
            .exists()
        )
        q = (
            select(DecisionSubscription.channel_id)
            .where(or_(DecisionSubscription.enabled.is_(True), pending_delivery))
            .order_by(DecisionSubscription.channel_id)
        )
        previous = queue.cursor
        ids = (
            list(await session.scalars(q.where(DecisionSubscription.channel_id > UUID(previous)).limit(4)))
            if previous
            else list(await session.scalars(q.limit(4)))
        )
        if not ids:
            ids = list(await session.scalars(q.limit(4)))
        if ids:
            queue.cursor = str(ids[-1])
        return ids
