"""Retired bridge bindings keep history and observe already resumed owners only."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from app.features.execution.flows import bridge
from app.features.execution.flows.adapters import RETIRED_BRIDGE, WorkerAdapter, get_worker_bindings
from app.features.execution.flows.models import FlowEnvironment, FlowPRLink, FlowRelease, FlowRun
from app.features.execution.flows.worker import FlowWorker
from app.features.project_management.pipeline_runs.models import PipelineRun, RunResumeReceipt
from autohub_sdk import FlowManifest, PipelineSpec, ReleaseSpec, TaskBinding, TaskRef
from sqlalchemy import select, update
from tests.integration.features.execution.flows.test_host import RELEASE_PATH, RUNS, command, drive, get, setup, start
from tests.integration.features.execution.flows.test_host import release as ordinary_release
from tests.integration.features.project_management.pipeline_runs import test_pipeline_runs_api as scenarios

pytestmark = pytest.mark.real_commit
github = scenarios.github
project = scenarios.project


def release(target="autohub.identity"):
    task = PipelineSpec(
        key="planhub.delivery",
        contract_version=1,
        title="Delivery",
        description="",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
    )
    return ReleaseSpec(
        manifest=FlowManifest(tasks=(task,)),
        bindings=(TaskBinding(task=TaskRef(key=task.key), executor="native", target=target),),
    )


@pytest.fixture
async def paused(client, project, github, clock, monkeypatch):
    monkeypatch.setattr(bridge, "get_current_utc_time", lambda: clock.now)
    response = await client.post(f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 7, "implemented": True})
    assert response.status_code == 201, response.text
    pipeline = response.json()
    response = await client.post(f"/api/v1/pipeline-runs/{pipeline['id']}/pause")
    assert response.status_code == 200, response.text
    return response.json()


async def legacy_run(
    client, session_maker, clock, paused, *, outstanding=False, receipted=False, target="autohub.pr_delivery:old"
):
    await setup(client, release())
    response = await client.post(
        RUNS,
        json={
            "provider": "planhub",
            "environment": "local",
            "task": {"key": "planhub.delivery"},
            "inputs": {"pipeline_run_id": paused["id"], "head_sha": paused["pull_snapshot"]["head_sha"]},
            "idempotency_key": "legacy-bridge",
        },
    )
    assert response.status_code == 202, response.text
    view = response.json()
    async with session_maker() as session:
        run = await session.get(FlowRun, UUID(view["run_id"]))
        snapshot = dict(run.snapshot)
        snapshot["bindings"] = {"planhub.delivery@1": {"executor": "native", "target": target}}
        run.snapshot = snapshot
        action = None
        if outstanding:
            action = await FlowWorker().runtime.plan(session, run, clock.now)
        session.add(
            FlowPRLink(
                pipeline_run_id=UUID(paused["id"]),
                flow_run_id=run.id,
                evidence={"legacy": True},
                delivery_attempt_id=action.attempt_id if action and receipted else None,
            )
        )
        if receipted:
            assert action is not None
            session.add(
                RunResumeReceipt(id=action.attempt_id, pipeline_run_id=UUID(paused["id"]), request_digest="a" * 64)
            )
        await session.commit()
    return await get(client, view), action


@pytest.mark.parametrize("target", ["autohub.sdd:old", "autohub.pr_delivery:old"])
async def test_bridge_registration_is_retired_without_creating_environment(client, owner, session_maker, target):
    response = await client.put(RELEASE_PATH, json=release(target).model_dump(mode="json"))
    assert response.status_code == 410 and response.json()["code"] == RETIRED_BRIDGE
    async with session_maker() as session:
        assert list(await session.scalars(select(FlowEnvironment))) == []
        assert list(await session.scalars(select(FlowRelease))) == []


async def test_legacy_release_cannot_activate_or_start_new_bridge_work(client, owner, session_maker):
    await setup(client, release())
    async with session_maker() as session:
        row = await session.scalar(select(FlowRelease))
        row.bindings = {"planhub.delivery@1": {"executor": "native", "target": "autohub.sdd:old"}}
        await session.commit()
    response = await client.post(RELEASE_PATH + "/activate", json={"expected_revision": 1})
    assert response.status_code == 410 and response.json()["code"] == RETIRED_BRIDGE
    response = await client.post(
        RUNS,
        json={
            "provider": "planhub",
            "environment": "local",
            "task": {"key": "planhub.delivery"},
            "inputs": {},
            "idempotency_key": "new",
        },
    )
    assert response.status_code == 410 and response.json()["code"] == RETIRED_BRIDGE
    async with session_maker() as session:
        assert list(await session.scalars(select(FlowRun))) == []


async def test_undispatched_legacy_work_is_retired_before_claim(
    client, owner, session_maker, clock, paused, monkeypatch
):
    view, _ = await legacy_run(client, session_maker, clock, paused)
    worker = FlowWorker()

    async def no_claim(*args, **kwargs):
        raise AssertionError("retired undispatched work must not claim a worker lease")

    monkeypatch.setattr(worker.repo, "claim", no_claim)
    assert await worker.advance(UUID(view["run_id"])) is True
    result = await get(client, view)
    assert result["status"] == "failed" and result["error"] == RETIRED_BRIDGE
    assert result["attempts"] == []
    async with session_maker() as session:
        link = await session.get(FlowPRLink, UUID(paused["id"]))
        assert link.canceled is True
        pipeline = await session.get(PipelineRun, UUID(paused["id"]))
        assert pipeline.state == "paused"
    response = await command(client, result, "resume")
    assert response.status_code == 410 and response.json()["code"] == RETIRED_BRIDGE


@pytest.mark.parametrize("target", ["autohub.sdd:old", "autohub.pr_delivery:old"])
async def test_outstanding_unreceipted_attempt_settles_terminally(client, owner, session_maker, clock, paused, target):
    view, action = await legacy_run(client, session_maker, clock, paused, outstanding=True, target=target)

    class NoEffectAdapter(WorkerAdapter):
        async def execute(self, action):
            raise AssertionError("retired intents cannot reach an external adapter")

    await FlowWorker(NoEffectAdapter()).advance(UUID(view["run_id"]))
    result = await get(client, view)
    assert result["status"] == "failed" and result["error"] == RETIRED_BRIDGE
    assert len(result["attempts"]) == 1 and result["attempts"][0]["error"] == RETIRED_BRIDGE
    assert action is not None
    async with session_maker() as session:
        assert await session.get(RunResumeReceipt, action.attempt_id) is None
        pipeline = await session.get(PipelineRun, UUID(paused["id"]))
        assert pipeline.state == "paused"
    assert await FlowWorker().advance(UUID(view["run_id"])) is False


async def test_receipt_backed_delivery_only_observes_existing_owner(
    client, owner, session_maker, clock, paused, monkeypatch
):
    view, action = await legacy_run(client, session_maker, clock, paused, outstanding=True, receipted=True)
    monkeypatch.setattr(bridge, "control", lambda: pytest.fail("observation must not resume an owner"))
    await FlowWorker().advance(UUID(view["run_id"]))
    waiting = await get(client, view)
    assert waiting["status"] == "waiting" and waiting["error"] == "pr-paused"
    assert waiting["attempts"][0]["output"]["pipeline_run_id"] == paused["id"]
    assert (await command(client, waiting, "approve")).status_code == 410
    async with session_maker() as session:
        await session.execute(update(PipelineRun).where(PipelineRun.id == UUID(paused["id"])).values(state="completed"))
        await session.commit()
    clock.advance()
    await FlowWorker().advance(UUID(view["run_id"]))
    await FlowWorker().advance(UUID(view["run_id"]))
    complete = await get(client, view)
    assert complete["status"] == "completed" and complete["output"]["state"] == "completed"
    assert len(complete["attempts"]) == 1
    async with session_maker() as session:
        receipts = list(
            await session.scalars(
                select(RunResumeReceipt).where(RunResumeReceipt.pipeline_run_id == UUID(paused["id"]))
            )
        )
        assert len(receipts) == 1 and action is not None and receipts[0].id == action.attempt_id
    assert await get(client, view) == complete


async def test_removed_delivery_environment_is_not_read(monkeypatch):
    monkeypatch.setenv("AUTOHUB_FLOW_DELIVERY_TARGETS", "this is no longer parsed")
    assert get_worker_bindings().targets == {}


async def test_receipt_backed_cancel_tombstones_and_uses_existing_owner_control(
    client, owner, session_maker, clock, paused, monkeypatch
):
    view, _ = await legacy_run(client, session_maker, clock, paused, outstanding=True, receipted=True)
    cancel_owner = AsyncMock()
    monkeypatch.setattr(bridge, "control", lambda: SimpleNamespace(cancel_run=cancel_owner))
    response = await command(client, view, "cancel")
    assert response.status_code == 200 and response.json()["status"] == "canceling"
    await FlowWorker().advance(UUID(view["run_id"]))
    result = await get(client, view)
    assert result["status"] == "canceled"
    cancel_owner.assert_awaited_once_with(UUID(paused["id"]))
    async with session_maker() as session:
        link = await session.get(FlowPRLink, UUID(paused["id"]))
        assert link.canceled is True


async def test_existing_legacy_start_replay_returns_history_without_new_effects(
    client, owner, session_maker, clock, paused
):
    view, _ = await legacy_run(client, session_maker, clock, paused)
    response = await client.post(
        RUNS,
        json={
            "provider": "planhub",
            "environment": "local",
            "task": {"key": "planhub.delivery"},
            "inputs": {"pipeline_run_id": paused["id"], "head_sha": paused["pull_snapshot"]["head_sha"]},
            "idempotency_key": "legacy-bridge",
        },
    )
    assert response.status_code == 202 and response.json()["run_id"] == view["run_id"]
    assert response.json()["attempts"] == []
    async with session_maker() as session:
        assert len(list(await session.scalars(select(FlowRun)))) == 1


async def test_legacy_approval_wait_retires_without_another_attempt(client, owner, session_maker, clock):
    await setup(client, ordinary_release())
    view = await drive(client, await start(client), clock)
    assert view["waiting_reason"] == "approval"
    async with session_maker() as session:
        run = await session.get(FlowRun, UUID(view["run_id"]))
        snapshot = dict(run.snapshot)
        bindings = dict(snapshot["bindings"])
        bindings["planhub.finalize@1"] = {"executor": "native", "target": "autohub.pr_delivery:old"}
        snapshot["bindings"] = bindings
        run.snapshot = snapshot
        await session.commit()
    await FlowWorker().advance(UUID(view["run_id"]))
    retired = await get(client, view)
    assert retired["status"] == "failed" and retired["error"] == RETIRED_BRIDGE
    assert len(retired["attempts"]) == len(view["attempts"])
    assert (await command(client, retired, "approve")).status_code == 410


async def test_old_check_cannot_use_a_delivery_receipt_to_continue(client, owner, session_maker, clock, paused):
    view, _ = await legacy_run(
        client, session_maker, clock, paused, outstanding=True, receipted=True, target="autohub.sdd:old"
    )
    await FlowWorker().advance(UUID(view["run_id"]))
    result = await get(client, view)
    assert result["status"] == "failed" and result["error"] == RETIRED_BRIDGE
    async with session_maker() as session:
        pipeline = await session.get(PipelineRun, UUID(paused["id"]))
        assert pipeline.state == "paused"
