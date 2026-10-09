import asyncio
from typing import Literal
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.execution.flows.adapters import (
    WorkerAdapter,
    WorkerResult,
)
from app.features.execution.flows.auth import get_flow_principal
from app.features.execution.flows.models import FlowCommand
from app.features.execution.flows.worker import FlowWorker
from autohub_sdk import (
    ApprovalStep,
    FlowManifest,
    FlowSpec,
    InputRef,
    PipelineSpec,
    ReleaseSpec,
    TaskBinding,
    TaskRef,
    TaskStep,
)
from sqlalchemy import select

pytestmark = pytest.mark.real_commit
RELEASE_PATH = "/api/v1/task-providers/planhub/environments/local/releases/release-1"
RUNS = "/api/v1/task-runs"
SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
    "additionalProperties": False,
}


def release(executor: Literal["native", "http"] = "native", target="autohub.identity"):
    tasks = tuple(
        PipelineSpec(
            key=f"planhub.{key}",
            contract_version=1,
            title=key,
            description="",
            input_schema=SCHEMA,
            output_schema=SCHEMA,
        )
        for key in ("prepare", "execute", "finalize")
    )
    flow = FlowSpec(
        key="planhub.delivery",
        title="Delivery",
        input_schema=SCHEMA,
        output_schema=SCHEMA,
        result_step="finalize",
        steps=(
            TaskStep(
                id="prepare",
                task=TaskRef(key="planhub.prepare"),
                inputs={"message": InputRef(source="run", path=("message",))},
            ),
            TaskStep(
                id="execute",
                task=TaskRef(key="planhub.execute"),
                max_attempts=3,
                inputs={"message": InputRef(source="step", step_id="prepare", path=("message",))},
            ),
            ApprovalStep(id="approval", deadline_seconds=60, revise_to="execute", max_revisions=1),
            TaskStep(
                id="finalize",
                task=TaskRef(key="planhub.finalize"),
                inputs={"message": InputRef(source="step", step_id="execute", path=("message",))},
            ),
        ),
    )
    return ReleaseSpec(
        manifest=FlowManifest(tasks=tasks, flows=(flow,)),
        bindings=tuple(TaskBinding(task=TaskRef(key=item.key), executor=executor, target=target) for item in tasks),
    )


def inputs(key="request-1", **changes):
    return {
        "provider": "planhub",
        "environment": "local",
        "task": {"key": "planhub.delivery", "contract_version": 1},
        "inputs": {"message": "hello"},
        "idempotency_key": key,
        **changes,
    }


async def setup(client, definition=None, path=RELEASE_PATH, expected=0):
    response = await client.put(path, json=(definition or release()).model_dump(mode="json"))
    assert response.status_code == 200, response.text
    active = await client.post(path + "/activate", json={"expected_revision": expected})
    assert active.status_code == 200, active.text
    return response.json()


async def start(client, **changes):
    response = await client.post(RUNS, json=inputs(**changes))
    assert response.status_code == 202, response.text
    return response.json()


async def get(client, run):
    response = await client.get(f"{RUNS}/{run['run_id']}")
    assert response.status_code == 200, response.text
    return response.json()


async def command(client, run, action, key=None):
    return await client.post(
        f"{RUNS}/{run['run_id']}/commands",
        json={"command_id": key or str(uuid4()), "expected_revision": run["revision"], "action": action},
    )


async def drive(client, run, clock, adapter=None):
    for _ in range(30):
        await FlowWorker(adapter).advance(UUID(run["run_id"]))
        run = await get(client, run)
        if run["status"] in ("completed", "failed", "canceled") or run["waiting_reason"] == "approval":
            return run
        clock.advance()
    raise AssertionError("flow did not settle")


async def test_real_catalog_and_request_idempotency(client, owner, clock):
    receipt = await setup(client)
    assert (await client.put(RELEASE_PATH, json=release().model_dump(mode="json"))).json() == receipt
    assert (await client.post(RELEASE_PATH + "/activate", json={"expected_revision": 0})).status_code == 409
    changed = release().model_dump(mode="json")
    changed["manifest"]["flows"][0]["title"] = "Other"
    assert (await client.put(RELEASE_PATH, json=changed)).status_code == 409
    run = await start(client)
    assert run["status"] == "queued" and run["attempts"] == []
    assert (await start(client))["run_id"] == run["run_id"]
    assert (await client.post(RUNS, json=inputs(inputs={"message": "changed"}))).status_code == 409
    assert await get(client, run) == run  # GET never drives execution.
    await setup(
        client, ReleaseSpec.model_validate(changed), path=RELEASE_PATH.replace("release-1", "release-2"), expected=1
    )
    assert (await get(client, run))["release_digest"] == receipt["digest"]
    assert (await start(client, key="new"))["release_id"] == "release-2"


async def test_approval_rework_and_command_receipt(client, owner, clock, session_maker):
    await setup(client)
    run = await drive(client, await start(client), clock)
    assert run["waiting_reason"] == "approval"
    revised = await command(client, run, "revise", "revise-1")
    assert revised.status_code == 200, revised.text
    again = await command(client, run, "revise", "revise-1")
    assert again.json() == revised.json()
    assert (await command(client, run, "approve", "revise-1")).status_code == 409
    run = await drive(client, revised.json(), clock)
    assert len(run["attempts"]) == 3
    assert (await command(client, run, "revise", "revise-2")).json()["code"] == "revision-limit"
    approved = await command(client, run, "approve", "approve-1")
    assert approved.status_code == 200, approved.text
    complete = await drive(client, approved.json(), clock)
    assert (complete["status"], complete["output"]) == ("completed", {"message": "hello"})
    assert (await command(client, run, "approve", "approve-1")).json() == approved.json()
    async with session_maker() as session:
        receipt = await session.scalar(select(FlowCommand).where(FlowCommand.command_key == "approve-1"))
        assert str(owner.machine_id) in receipt.actor and str(owner.key_id) in receipt.actor


async def test_owner_and_scope_isolation(client, owner, app, clock):
    await setup(client)
    run = await drive(client, await start(client), clock)
    foreign = owner.model_copy(update={"machine_id": uuid4()})
    app.dependency_overrides[get_flow_principal] = lambda: foreign
    assert (await client.get(f"{RUNS}/{run['run_id']}")).status_code == 403
    assert (await client.put(RELEASE_PATH, json=release().model_dump(mode="json"))).status_code == 403
    no_approval = owner.model_copy(update={"scopes": frozenset({"autohub:task:write", "autohub:task:read"})})
    app.dependency_overrides[get_flow_principal] = lambda: no_approval
    assert (await command(client, run, "approve")).status_code == 403
    rotated = owner.model_copy(update={"key_id": uuid4()})
    app.dependency_overrides[get_flow_principal] = lambda: rotated
    assert (await command(client, run, "approve")).status_code == 200


class ScriptedAdapter(WorkerAdapter):
    def __init__(self, fail=False, pending=False):
        self.operations = []
        self.results = {}
        self.fail = fail
        self.pending = pending
        self.crash = False

    async def execute(self, action):
        self.operations.append((action.operation, action.attempt_id))
        if action.operation == "cancel":
            result = WorkerResult(attempt_id=action.attempt_id, status="canceled")
        elif action.operation == "inspect":
            return self.results.get(action.attempt_id, WorkerResult(attempt_id=action.attempt_id, status="not_found"))
        elif self.fail and action.task.key == "planhub.execute":
            result = WorkerResult(attempt_id=action.attempt_id, status="failed", error="test-failure")
        else:
            result = WorkerResult(
                attempt_id=action.attempt_id, status="pending" if self.pending else "completed", output=action.inputs
            )
        self.results[action.attempt_id] = result
        if self.crash:
            self.crash = False
            raise SimulatedProcessDeath()
        return result


class SimulatedProcessDeath(BaseException):
    pass


async def test_crash_after_effect_recovers_same_attempt(client, owner, clock):
    await setup(client)
    run = await start(client)
    adapter = ScriptedAdapter()
    adapter.crash = True
    with pytest.raises(SimulatedProcessDeath):
        await FlowWorker(adapter).advance(UUID(run["run_id"]))
    persisted = await get(client, run)
    assert persisted["attempts"][0]["status"] == "running"
    attempt_id = adapter.operations[0][1]
    await FlowWorker(adapter).advance(UUID(run["run_id"]))
    assert adapter.operations == [("submit", attempt_id), ("inspect", attempt_id)]
    assert len((await get(client, run))["attempts"]) == 1


async def test_explicit_resume_cannot_reset_attempt_budget(client, owner, clock):
    await setup(client)
    adapter = ScriptedAdapter(fail=True)
    run = await drive(client, await start(client), clock, adapter)
    assert run["status"] == "failed"
    for _ in range(2):
        resumed = await command(client, run, "resume")
        assert resumed.status_code == 200, resumed.text
        run = await drive(client, resumed.json(), clock, adapter)
    assert (await command(client, run, "resume")).json()["code"] == "attempt-limit"
    assert len(run["attempts"]) == 4


async def test_deadline_and_schema_errors(client, owner, clock):
    await setup(client)
    bad = await client.post(RUNS, json=inputs(inputs={"message": 42}))
    assert bad.status_code == 422 and bad.json()["code"] == "schema-invalid"
    run = await drive(client, await start(client), clock)
    clock.advance(60)
    assert (await command(client, run, "approve")).json()["code"] == "approval-expired"
    assert (await get(client, run))["status"] == "waiting"
    await FlowWorker().advance(UUID(run["run_id"]))
    expired = await get(client, run)
    assert (expired["status"], expired["error"]) == ("failed", "approval-deadline")
    invalid_binding = release(target="unregistered")
    response = await client.put(
        RELEASE_PATH.replace("release-1", "invalid"), json=invalid_binding.model_dump(mode="json")
    )
    assert response.status_code == 422


async def test_cancel_and_inflight_revision_fence(client, owner, clock, session_maker):
    await setup(client)
    run = await start(client)
    entered, resume = asyncio.Event(), asyncio.Event()

    class PausedAdapter(WorkerAdapter):
        async def execute(self, action):
            entered.set()
            await resume.wait()
            return WorkerResult(attempt_id=action.attempt_id, status="completed", output=action.inputs)

    advancing = asyncio.create_task(FlowWorker(PausedAdapter()).advance(UUID(run["run_id"])))
    await asyncio.wait_for(entered.wait(), timeout=3)
    run = await get(client, run)
    try:
        canceled = await command(client, run, "cancel")
        assert canceled.status_code == 200 and canceled.json()["status"] == "canceling"
    finally:
        resume.set()
    assert await advancing is False
    stale_result = await get(client, run)
    assert stale_result["status"] == "canceling" and stale_result["output"] is None
    await FlowWorker().advance(UUID(run["run_id"]))
    assert (await get(client, run))["status"] == "canceled"


async def test_authoritative_absence_resubmits_same_intent(client, owner, clock, session_maker):
    await setup(client)
    run = await start(client)
    adapter = ScriptedAdapter()

    # Fail before acceptance, preserving an unknown intent.
    async def unavailable(action):
        raise httpx.ConnectError("test disconnect")

    original = adapter.execute
    adapter.execute = unavailable
    await FlowWorker(adapter).advance(UUID(run["run_id"]))
    adapter.execute = original
    clock.advance()
    await FlowWorker(adapter).advance(UUID(run["run_id"]))  # inspect authoritative absence
    await FlowWorker(adapter).advance(UUID(run["run_id"]))  # resubmit same ID
    assert len({attempt for _, attempt in adapter.operations}) == 1
    assert [operation for operation, _ in adapter.operations] == ["inspect", "submit"]
    assert len((await get(client, run))["attempts"]) == 1


async def test_worker_lease_and_concurrent_commands_postgres(client, owner, clock, is_postgres):
    if not is_postgres:
        pytest.skip("real PostgreSQL row/lease concurrency")
    await setup(client)
    one, two = await asyncio.gather(start(client), start(client))
    assert one["run_id"] == two["run_id"]
    adapter = ScriptedAdapter()
    await asyncio.gather(*(FlowWorker(adapter).advance(UUID(one["run_id"])) for _ in range(4)))
    # Later tasks may legitimately advance after the first lease is released, but each step has one attempt.
    run = await drive(client, one, clock, adapter)
    assert len(run["attempts"]) == 2
    responses = await asyncio.gather(command(client, run, "approve", "one"), command(client, run, "approve", "two"))
    assert sorted(response.status_code for response in responses) == [200, 409]


async def test_expired_lease_reclamation_rejects_old_worker_result(client, owner, clock):
    await setup(client)
    run = await start(client)
    entered, resume = asyncio.Event(), asyncio.Event()
    adapter = ScriptedAdapter()

    class StaleAdapter(WorkerAdapter):
        async def execute(self, action):
            entered.set()
            await resume.wait()
            return WorkerResult(attempt_id=action.attempt_id, status="completed", output={"message": "stale"})

    pending = asyncio.create_task(FlowWorker(StaleAdapter()).advance(UUID(run["run_id"])))
    await asyncio.wait_for(entered.wait(), timeout=3)
    clock.advance(61)
    await FlowWorker(adapter).advance(UUID(run["run_id"]))  # new lease inspects missing old intent
    resume.set()
    assert await pending is False
    await FlowWorker(adapter).advance(UUID(run["run_id"]))  # reuse same ID
    actual = await get(client, run)
    assert len(actual["attempts"]) == 1
    assert actual["attempts"][0]["output"] == {"message": "hello"}


async def test_host_limits_and_nonfinite_json_are_wire_errors(client, owner):
    body = release().model_dump(mode="json")
    body["manifest"]["flows"][0]["steps"][2]["deadline_seconds"] = 31536001
    rejected = await client.put(RELEASE_PATH, json=body)
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "contract-limit"
    await setup(client)
    rejected = await client.post(
        RUNS,
        content='{"provider":"planhub","environment":"local","task":{"key":"planhub.delivery"},"inputs":{"message":NaN},"idempotency_key":"bad-json"}',
        headers={"Content-Type": "application/json"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "json-invalid"


async def test_worker_output_schema_blocks_downstream_tasks(client, owner):
    await setup(client)
    run = await start(client)

    class InvalidOutput(WorkerAdapter):
        async def execute(self, action):
            return WorkerResult(attempt_id=action.attempt_id, status="completed", output={"message": 42})

    await FlowWorker(InvalidOutput()).advance(UUID(run["run_id"]))
    failed = await get(client, run)
    assert failed["status"] == "failed" and failed["error"] == "worker-output-invalid"
    assert len(failed["attempts"]) == 1 and failed["current_step"] == "prepare"
    assert failed["output"] is None


def test_worker_nonfinite_output_is_invalid_protocol():
    with pytest.raises(ValueError):
        WorkerResult(attempt_id=uuid4(), status="completed", output={"value": float("nan")})


async def test_expected_release_rejects_activation_race_before_creating_run(client, owner, session_maker):
    from app.features.execution.flows.models import FlowRun

    await setup(client)
    response = await client.post(RUNS, json={**inputs(), "expected_release_id": "wrong-release"})
    assert response.status_code == 409 and response.json()["code"] == "release-mismatch"
    async with session_maker() as session:
        assert list(await session.scalars(select(FlowRun))) == []
    run = await start(client)
    assert run["release_id"] == "release-1"
