from __future__ import annotations

import builtins
from datetime import timedelta
from uuid import UUID, uuid4

from app.features.project_management.connection_tests.models import ACTIVE, TEST_TASK, ConnectionTest
from app.features.project_management.projects.errors import ProjectError
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class ConnectionTestRepository:
    async def get(self, session: AsyncSession, test_id: UUID) -> ConnectionTest | None:
        return await session.get(ConnectionTest, test_id)

    async def list(self, session: AsyncSession, project_id: UUID) -> list[ConnectionTest]:
        rows = await session.scalars(
            select(ConnectionTest)
            .where(ConnectionTest.project_id == project_id)
            .order_by(ConnectionTest.created_at.desc(), ConnectionTest.id)
            .limit(30)
        )
        return list(rows)

    async def create(self, session: AsyncSession, row: ConnectionTest) -> ConnectionTest:
        session.add(row)
        session.add(
            ScheduleConfig(
                id=row.id,
                name=f"Connection test {row.id}",
                task_func=TEST_TASK,
                interval_seconds=60,
                payload={"test_id": str(row.id)},
                enabled=True,
                next_run_at=get_current_utc_time(),
            )
        )
        await session.flush()
        await session.refresh(row)
        return row

    async def claim(self, session: AsyncSession, test_id: UUID) -> tuple[ConnectionTest, UUID] | None:
        now, token = get_current_utc_time(), uuid4()
        result = await session.execute(
            update(ConnectionTest)
            .where(
                ConnectionTest.id == test_id,
                or_(ConnectionTest.status == ACTIVE, ConnectionTest.cleanup_status != "completed"),
                or_(ConnectionTest.lease_until.is_(None), ConnectionTest.lease_until < now),
            )
            .values(lease_token=token, lease_until=now + timedelta(seconds=90))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            return None
        row = await self.get(session, test_id)
        assert row is not None
        await session.refresh(row)
        return row, token

    async def finish_step(self, session: AsyncSession, row: ConnectionTest, token: UUID) -> bool:
        result = await session.execute(
            update(ConnectionTest)
            .where(
                ConnectionTest.id == row.id,
                ConnectionTest.lease_token == token,
            )
            .values(
                status=row.status,
                phase=row.phase,
                cleanup_status=row.cleanup_status,
                detail=row.detail,
                evidence=row.evidence,
                finished_at=row.finished_at,
                lease_token=None,
                lease_until=None,
            )
        )
        if result.rowcount == 1 and row.status != ACTIVE and row.cleanup_status == "completed":  # type: ignore[attr-defined]
            await session.execute(update(ScheduleConfig).where(ScheduleConfig.id == row.id).values(enabled=False))
        return result.rowcount == 1  # type: ignore[attr-defined]

    async def cancel(self, session: AsyncSession, test_id: UUID) -> None:
        await session.execute(
            update(ConnectionTest)
            .where(
                ConnectionTest.id == test_id,
                ConnectionTest.status == ACTIVE,
            )
            .values(cancel_requested=True)
        )

    async def owns_pull(self, session: AsyncSession, repository: str, number: int) -> bool:
        return (
            await session.scalar(
                select(ConnectionTest.id)
                .where(
                    ConnectionTest.repository == repository,
                    or_(
                        ConnectionTest.evidence["pull_number"].as_integer() == number,
                        ConnectionTest.evidence["owned_pulls"][str(number)].as_string().is_not(None),
                    ),
                )
                .limit(1)
            )
            is not None
        )

    async def protected_heads(self, session: AsyncSession, repository: str) -> builtins.list[str]:
        """Only undiscovered provider output needs ancestry checks; known PR IDs remain protected forever.

        Pending output discovery lasts at most the cancellation grace period. Completed history never adds
        GitHub requests to unrelated PRs. The cap defers enrollment rather than making an unbounded scan.
        """
        cutoff = get_current_utc_time() - timedelta(days=1)
        rows = list(
            await session.scalars(
                select(ConnectionTest.evidence)
                .where(
                    ConnectionTest.repository == repository,
                    ConnectionTest.cleanup_status != "completed",
                    or_(ConnectionTest.status == ACTIVE, ConnectionTest.finished_at > cutoff),
                    or_(
                        ConnectionTest.evidence["output_discovery_pending"].as_boolean().is_(True),
                        # Compatibility for tests dispatched before recipe metadata existed.
                        ConnectionTest.evidence["output_discovery_pending"].as_boolean().is_(None)
                        & ConnectionTest.evidence["jules_create_attempted"].as_boolean().is_(True),
                    ),
                )
                .limit(21)
            )
        )
        if len(rows) > 20:
            raise ProjectError(
                409, "Too many unresolved connection tests; finish their reconciliation before enrolling PRs"
            )
        return list({e["initial_sha"] for e in rows if isinstance(e.get("initial_sha"), str)})
