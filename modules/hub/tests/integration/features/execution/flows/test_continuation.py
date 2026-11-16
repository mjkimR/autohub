"""Maintenance drains ready work without skipping genuine waits or durable recovery."""

import asyncio
from uuid import UUID

import pytest
from app.features.execution.flows import worker
from app.features.execution.flows.worker import FlowWorker
from tests.integration.features.execution.flows.test_host import (
    ScriptedAdapter,
    SimulatedProcessDeath,
    command,
    get,
    setup,
    start,
)

pytestmark = pytest.mark.real_commit


async def test_tick_drains_tasks_to_approval_and_finishes_after_approval(client, owner, clock):
    await setup(client)
    run = await start(client)
    await FlowWorker().tick()
    waiting = await get(client, run)
    assert waiting["waiting_reason"] == "approval"
    assert len(waiting["attempts"]) == 2
    approved = await command(client, waiting, "approve")
    assert approved.status_code == 200
    await FlowWorker().tick()
    finished = await get(client, run)
    assert finished["status"] == "completed"
    assert finished["output"] == {"message": "hello"}


async def test_pending_result_stops_without_immediate_poll(client, owner, clock):
    await setup(client)
    run = await start(client)
    adapter = ScriptedAdapter(pending=True)
    await FlowWorker(adapter).advance_until_wait(UUID(run["run_id"]))
    assert [operation for operation, _ in adapter.operations] == ["submit"]
    waiting = await get(client, run)
    assert waiting["waiting_reason"] == "external-result"
    await FlowWorker(adapter).advance_until_wait(UUID(run["run_id"]))
    assert len(adapter.operations) == 1


async def test_absence_recovery_resubmits_same_attempt_in_one_invocation(client, owner, clock):
    await setup(client)
    run = await start(client)
    adapter = ScriptedAdapter()
    adapter.crash = True
    with pytest.raises(SimulatedProcessDeath):
        await FlowWorker(adapter).advance(UUID(run["run_id"]))
    first_id = adapter.operations[0][1]
    adapter.results.clear()
    await FlowWorker(adapter).advance_until_wait(UUID(run["run_id"]))
    assert adapter.operations[1:3] == [("inspect", first_id), ("submit", first_id)]
    assert (await get(client, run))["waiting_reason"] == "approval"


async def test_step_budget_leaves_due_work_for_next_tick(client, owner, clock, monkeypatch):
    await setup(client)
    run = await start(client)
    monkeypatch.setattr(worker, "CONTINUE_MAX_STEPS", 1)
    await FlowWorker().tick()
    assert len((await get(client, run))["attempts"]) == 1
    await FlowWorker().tick()
    assert len((await get(client, run))["attempts"]) == 2
    await FlowWorker().tick()
    assert (await get(client, run))["waiting_reason"] == "approval"


async def test_timeout_releases_lease_and_keeps_intent(client, owner, clock, monkeypatch):
    await setup(client)
    run = await start(client)

    class SlowAdapter(ScriptedAdapter):
        async def execute(self, action):
            await asyncio.Event().wait()
            return await super().execute(action)

    monkeypatch.setattr(worker, "CONTINUE_SECONDS", 0.05)
    await FlowWorker(SlowAdapter()).advance_until_wait(UUID(run["run_id"]))
    stalled = await get(client, run)
    assert len(stalled["attempts"]) == 1
    monkeypatch.setattr(worker, "CONTINUE_SECONDS", 20)
    await FlowWorker().advance_until_wait(UUID(run["run_id"]))
    assert (await get(client, run))["waiting_reason"] == "approval"
