from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.features.ai_catalogs.models import AICatalog, AICatalogSession
from app.features.execution.tasks.domains.maintenance import task as worker
from app.features.execution.tasks.domains.maintenance.repos import MaintenanceRepository
from app.features.execution.tasks.domains.pipeline import connection_probe
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app.features.scheduling.schedule_configs.system import (
    MAINTENANCE_ID,
    MAINTENANCE_TASK,
    ensure_maintenance_schedule,
)
from app_testing_base import utc_now
from sqlalchemy import delete, select, update
from tests.integration.features.project_management.connection_tests import test_connection_tests as probes

github = probes.github
project = probes.project
start = probes.start
step = probes.step


pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_singleton_repair_preserves_due_time_and_is_protected(client, session):
    await ensure_maintenance_schedule(session)
    row = await session.get(ScheduleConfig, MAINTENANCE_ID)
    assert row is not None and row.enabled and row.task_func == MAINTENANCE_TASK
    due = utc_now() + timedelta(hours=1)
    row.next_run_at = due
    await session.commit()
    await ensure_maintenance_schedule(session)
    await session.commit()
    await session.refresh(row)
    assert row.next_run_at.replace(tzinfo=due.tzinfo) == due
    path = f"/api/v1/schedule_configs/{MAINTENANCE_ID}"
    for patch in ({"enabled": False}, {"payload": {"test_id": "wrong"}}, {"task_func": "hello_world"}):
        assert (await client.patch(path, json=patch)).status_code == 409
    body = {"name": "Duplicate", "task_func": MAINTENANCE_TASK, "interval_seconds": 60}
    assert (await client.post("/api/v1/schedule_configs", json=body)).status_code == 409
    assert (await client.put(path, json=body)).status_code == 409
    assert (await client.delete(path)).status_code == 409
    ordinary = await client.post("/api/v1/schedule_configs", json={**body, "task_func": "hello_world"})
    assert (await client.patch(f"/api/v1/schedule_configs/{ordinary.json()['id']}", json=body)).status_code == 409
    # Simulate an operational deletion outside the protected API, then repair at the real trigger boundary.
    await session.execute(delete(ScheduleConfig).where(ScheduleConfig.id == MAINTENANCE_ID))
    await session.commit()
    assert (await client.post("/api/v1/dispatchers/trigger")).status_code == 200
    session.expire_all()
    assert (
        len(list(await session.scalars(select(ScheduleConfig).where(ScheduleConfig.task_func == MAINTENANCE_TASK))))
        == 1
    )


async def test_disabled_system_schedule_is_repaired(session):
    await ensure_maintenance_schedule(session)
    await session.execute(update(ScheduleConfig).where(ScheduleConfig.id == MAINTENANCE_ID).values(enabled=False))
    await ensure_maintenance_schedule(session)
    session.expire_all()
    assert (await session.get(ScheduleConfig, MAINTENANCE_ID)).enabled


async def test_cleanup_continues_on_disabled_project_without_a_probe_schedule(
    client, session, project, github, monkeypatch, credential_key_provider
):
    monkeypatch.setattr(connection_probe, "get_credential_key_provider", lambda: credential_key_provider)
    test = await step(client, await step(client, await start(client, project)))
    github.push(test["id"])
    test = await step(client, test)
    assert test["status"] == "succeeded"
    assert await session.get(ScheduleConfig, UUID(test["id"])) is None
    await session.execute(update(Project).where(Project.id == UUID(project["id"])).values(enabled=False))
    await session.commit()
    await worker.maintain_task(worker.MaintenancePayload())
    session.expire_all()
    stored = await session.get(ConnectionTest, UUID(test["id"]))
    assert stored.cleanup_status == "completed"
    assert github.branch is None and github.pr["state"] == "closed"
    assert await MaintenanceRepository().pending_tests(session) == []


async def test_pending_sessions_are_collected_without_agent_schedules_and_failures_are_isolated(session, monkeypatch):
    rows = []
    for key in ("broken", "orphan", "adoption", "finished"):
        c = AICatalog(key=key, name=key, kind="jules", adapter="jules-api", enabled=False)
        session.add(c)
        await session.flush()
        rows.append(c)
        session.add(
            AICatalogSession(
                ai_catalog_id=c.id,
                title=key,
                work_type="task",
                state="in_progress" if key in ("broken", "orphan") else "completed",
                pull_request_url="https://github.com/owner/app/pull/3" if key == "adoption" else None,
            )
        )
    await session.commit()
    assert set(await MaintenanceRepository().pending_catalogs(session)) == {"broken", "orphan", "adoption"}

    async def sync(key):
        if key == "broken":
            raise RuntimeError("provider unavailable")

    service = AsyncMock()
    service.sync.side_effect = sync
    monkeypatch.setattr(worker, "jules_service", lambda: service)
    with pytest.raises(RuntimeError, match="1 item"):
        await worker.maintain_task(worker.MaintenancePayload())
    assert {call.args[0] for call in service.sync.await_args_list} == {"broken", "orphan", "adoption"}


async def test_concurrent_postgres_repair_creates_one_schedule(session):
    import asyncio

    from app_layer_base.core.database.transaction import AsyncTransaction

    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("Concurrent startup uses independent PostgreSQL transactions")
    await session.commit()

    barrier = asyncio.Barrier(4)

    async def repair():
        async with AsyncTransaction() as db:
            await barrier.wait()
            await ensure_maintenance_schedule(db)

    # Exercise fresh inserts repeatedly; conflicts on the secondary unique index are timing-dependent.
    for _ in range(10):
        await session.execute(delete(ScheduleConfig).where(ScheduleConfig.id == MAINTENANCE_ID))
        await session.commit()
        await asyncio.gather(*(repair() for _ in range(4)))
        configs = list(
            await session.scalars(select(ScheduleConfig).where(ScheduleConfig.task_func == MAINTENANCE_TASK))
        )
        assert len(configs) == 1 and configs[0].id == MAINTENANCE_ID
