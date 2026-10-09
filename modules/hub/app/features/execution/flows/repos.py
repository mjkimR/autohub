from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .errors import FlowError
from .models import FlowAttempt, FlowCommand, FlowEnvironment, FlowRelease, FlowRun, FlowStep

ACTIVE = ("queued", "running", "waiting", "canceling")


class FlowRepository:
    @staticmethod
    async def insert_once(session: AsyncSession, model, values: dict) -> None:
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        await session.execute(insert(model).values(**values).on_conflict_do_nothing())

    async def environment(self, session, provider, environment, *, lock=False):
        stmt = select(FlowEnvironment).where(
            FlowEnvironment.provider == provider, FlowEnvironment.environment == environment
        )
        if lock:
            stmt = stmt.with_for_update()
        return await session.scalar(stmt)

    async def release(self, session, provider, environment, release_id):
        return await session.scalar(
            select(FlowRelease).where(
                FlowRelease.provider == provider,
                FlowRelease.environment == environment,
                FlowRelease.release_id == release_id,
            )
        )

    async def request(self, session, provider, environment, key):
        return await session.scalar(
            select(FlowRun).where(
                FlowRun.provider == provider, FlowRun.environment == environment, FlowRun.request_key == key
            )
        )

    async def run(self, session, run_id, *, lock=False):
        return await session.get(FlowRun, run_id, with_for_update=lock, populate_existing=True)

    async def steps(self, session, run_id):
        return list(
            await session.scalars(select(FlowStep).where(FlowStep.run_id == run_id).order_by(FlowStep.position))
        )

    async def attempts(self, session, run_id):
        return list(
            await session.scalars(
                select(FlowAttempt)
                .join(FlowStep, FlowAttempt.step_id == FlowStep.id)
                .where(FlowAttempt.run_id == run_id)
                .order_by(FlowStep.position, FlowAttempt.number)
            )
        )

    async def command(self, session, run_id, key):
        return await session.scalar(
            select(FlowCommand).where(FlowCommand.run_id == run_id, FlowCommand.command_key == key)
        )

    @staticmethod
    async def bump(session, run: FlowRun, now: datetime):
        old_revision = run.revision
        result = await session.execute(
            update(FlowRun)
            .where(FlowRun.id == run.id, FlowRun.revision == old_revision)
            .values(revision=old_revision + 1, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise FlowError(409, "stale-revision", "run revision changed")
        run.revision = old_revision + 1
        run.updated_at = now

    async def activate(self, session, row: FlowEnvironment, release_id: str, expected: int, now: datetime):
        if row.revision != expected:
            raise FlowError(409, "stale-revision", "active release revision changed")
        revision = expected + int(row.active_release_id != release_id)
        result = await session.execute(
            update(FlowEnvironment)
            .where(
                FlowEnvironment.provider == row.provider,
                FlowEnvironment.environment == row.environment,
                FlowEnvironment.revision == expected,
            )
            .values(active_release_id=release_id, revision=revision, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise FlowError(409, "stale-revision", "active release revision changed")
        return revision

    async def claim(self, session, run_id: UUID, token: UUID, now: datetime, seconds=60):
        result = await session.execute(
            update(FlowRun)
            .where(
                FlowRun.id == run_id,
                FlowRun.status.in_(ACTIVE),
                or_(FlowRun.lease_token.is_(None), FlowRun.lease_expires_at <= now),
                or_(FlowRun.next_action_at.is_(None), FlowRun.next_action_at <= now),
            )
            .values(lease_token=token, lease_expires_at=now + timedelta(seconds=seconds))
        )
        return result.rowcount == 1

    async def fenced(self, session, run_id, token, now):
        return await session.scalar(
            select(FlowRun)
            .where(FlowRun.id == run_id, FlowRun.lease_token == token, FlowRun.lease_expires_at > now)
            .with_for_update()
        )

    async def release_lease(self, session, run_id, token):
        await session.execute(
            update(FlowRun)
            .where(FlowRun.id == run_id, FlowRun.lease_token == token)
            .values(lease_token=None, lease_expires_at=None)
        )

    async def ready(self, session, now, limit=32):
        return list(
            await session.scalars(
                select(FlowRun.id)
                .where(
                    FlowRun.status.in_(ACTIVE),
                    or_(FlowRun.next_action_at.is_(None), FlowRun.next_action_at <= now),
                    or_(FlowRun.lease_token.is_(None), FlowRun.lease_expires_at <= now),
                )
                .order_by(FlowRun.next_action_at.asc().nullsfirst(), FlowRun.created_at, FlowRun.id)
                .limit(limit)
            )
        )
