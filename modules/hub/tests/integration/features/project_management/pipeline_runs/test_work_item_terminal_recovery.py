import asyncio
from uuid import UUID

import pytest
from app.features.project_management.pipeline_runs.models import ExecutionDelivery
from app.features.project_management.work_plans.recovery_tick import RecoveryTick
from sqlalchemy import func, select

from tests.integration.features.project_management.work_plans.conftest import setup_work
from tests.integration.features.project_management.work_plans.test_item_recovery import command, endpoint, terminal
from tests.integration.features.project_management.work_plans.test_work_plans import due

__all__ = ["setup_work"]
pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_ordinary_enrollment_wins_during_recovery_io_without_loser_dispatch(
    client, setup_work, session, monkeypatch
):
    if session.bind.dialect.name != "postgresql":
        pytest.skip("requires actual PostgreSQL locking and commits")
    project, _, worker, plan, item, _run = await terminal(client, setup_work, session)
    root = endpoint(project, plan, item)
    assert (await client.post(root + "/recover", json=command(plan, item))).status_code == 200
    read_done, enrolled = asyncio.Event(), asyncio.Event()
    original = RecoveryTick.apply

    async def wait_for_enrollment(self, *args, **kwargs):
        read_done.set()
        await asyncio.wait_for(enrolled.wait(), 10)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(RecoveryTick, "apply", wait_for_enrollment)
    await due(session)
    task = asyncio.create_task(worker.advance_project(UUID(project["id"])))
    try:
        await asyncio.wait_for(read_done.wait(), 10)
        response = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 100})
        assert response.status_code == 201, response.text
    finally:
        enrolled.set()
        await task
    record = (await client.get(root + "/recoveries")).json()["items"][0]
    assert record["state"] == "refused"
    assert await session.scalar(select(func.count()).select_from(ExecutionDelivery)) == 0
