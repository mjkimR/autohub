import asyncio
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.features.execution.tasks.domains.maintenance import task as worker
from app.features.execution.tasks.domains.maintenance.repos import MaintenanceRepository
from app_layer_base.core.database.transaction import AsyncTransaction

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.fixture
def stalled_work(monkeypatch):
    tests = [UUID(int=i) for i in range(1, 7)]
    catalogs = [f"catalog-{i}" for i in range(6)]
    monkeypatch.setattr(MaintenanceRepository, "pending_tests", AsyncMock(return_value=tests))
    monkeypatch.setattr(MaintenanceRepository, "pending_catalogs", AsyncMock(return_value=catalogs))
    monkeypatch.setattr(worker.HistoryRetentionUseCase, "execute", AsyncMock())
    started = {"tests": [], "catalogs": []}
    all_slots_used = asyncio.Event()
    stalled = asyncio.Event()
    active = 0

    async def block(group, item):
        nonlocal active
        started[group].append(item)
        active += 1
        if active == 4:
            all_slots_used.set()
        try:
            await stalled.wait()
        finally:
            active -= 1

    async def probe(payload):
        await block("tests", payload.test_id)

    async def sync(key):
        await block("catalogs", key)

    service = AsyncMock()
    service.sync.side_effect = sync
    monkeypatch.setattr(worker, "connection_test_task", probe)
    monkeypatch.setattr(worker, "jules_service", lambda: service)

    async def cancel_tick():
        all_slots_used.clear()
        task = asyncio.create_task(worker.maintain_task(worker.MaintenancePayload()))
        try:
            # Reproduce the dispatcher's cancellation with all four slots occupied, without timed sleeps.
            await asyncio.wait_for(all_slots_used.wait(), timeout=5)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert active == 0

    return tests, catalogs, started, cancel_tick


async def test_both_groups_progress_and_rotate_after_canceled_ticks(session, stalled_work):
    tests, catalogs, started, cancel_tick = stalled_work
    await session.commit()
    for tick in range(3):
        await cancel_tick()
        assert len(started["tests"]) == len(started["catalogs"]) == (tick + 1) * 2
    # Each invocation creates a fresh repository and reads the persisted cursors.
    assert started["tests"] == tests
    assert started["catalogs"] == catalogs


@pytest.mark.parametrize("group", ["tests", "catalogs"])
async def test_one_group_uses_four_slots_and_wraps_after_cancellation(session, stalled_work, monkeypatch, group):
    tests, catalogs, started, cancel_tick = stalled_work
    other = "catalogs" if group == "tests" else "tests"
    monkeypatch.setattr(MaintenanceRepository, f"pending_{other}", AsyncMock(return_value=[]))
    await session.commit()
    await cancel_tick()
    assert len(started[group]) == 4 and started[other] == []
    await cancel_tick()
    expected = tests if group == "tests" else catalogs
    assert started[group] == expected + expected[:2]


async def test_overlapping_postgres_ticks_advance_the_shared_cursor(session):
    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("Concurrent cursors use independent PostgreSQL transactions")
    await session.commit()
    pending = [f"catalog-{i}" for i in range(6)]

    async def select_next():
        async with AsyncTransaction() as db:
            return await MaintenanceRepository().next_item(db, "catalogs", pending)

    selected = await asyncio.gather(*(select_next() for _ in range(4)))
    assert set(selected) == set(pending[:4])


async def test_cursor_handles_removed_and_new_pending_items(session):
    repo = MaintenanceRepository()
    assert await repo.next_item(session, "catalogs", ["b", "d"]) == "b"
    await session.commit()
    # The previous item disappeared and a new item sorts before it; wrap after trying the later item.
    assert await repo.next_item(session, "catalogs", ["a", "d"]) == "d"
    await session.commit()
    assert await repo.next_item(session, "catalogs", ["a", "d"]) == "a"
