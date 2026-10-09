import asyncio
import json
import socket
from uuid import UUID, uuid4

import httpx
import pytest
import uvicorn
from app.features.execution.flows.adapters import WorkerBindings, get_worker_bindings
from app.features.execution.flows.auth import FLOW_SCOPES, get_flow_principal
from app.features.execution.flows.models import FlowRun
from app.features.execution.flows.worker import FlowWorker
from app.main import create_app
from app_layer_base.base.models.mixin import Base
from app_layer_base.core.database import engine as db_engine
from app_prebuilt_auth.api_key.schemas import MachinePrincipal
from autohub_sdk import AutoHubClient, RunCommand, RunRequest, TaskRef
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tests.integration.features.execution.flows.test_host import (
    RELEASE_PATH,
    command,
    drive,
    get,
    release,
    setup,
    start,
)

pytestmark = pytest.mark.real_commit


async def test_sdk_http_client_calls_actual_host(app, session, owner, clock):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="error"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        for _ in range(300):
            if server.started:
                break
            if task.done():
                await task
                raise AssertionError("server failed to start")
            await asyncio.sleep(0.01)
        assert server.started
        sdk = AutoHubClient(f"http://127.0.0.1:{listener.getsockname()[1]}", api_key="test-scope-override")
        definition = release()
        receipt = await asyncio.to_thread(sdk.register_release, "planhub", "local", "release-1", definition)
        assert receipt.digest == definition.digest()
        await asyncio.to_thread(sdk.activate_release, "planhub", "local", "release-1", expected_revision=0)
        request = RunRequest(
            provider="planhub",
            environment="local",
            task=TaskRef(key="planhub.delivery"),
            inputs={"message": "sdk"},
            idempotency_key="sdk-request",
        )
        run = await asyncio.to_thread(sdk.start_run, request)
        assert (await asyncio.to_thread(sdk.start_run, request)).run_id == run.run_id
        for _ in range(3):
            await FlowWorker().advance(UUID(run.run_id))
        wait = await asyncio.to_thread(sdk.get_run, run.run_id)
        assert wait.waiting_reason == "approval"
        await asyncio.to_thread(
            sdk.command, run.run_id, RunCommand(command_id="approve", expected_revision=wait.revision, action="approve")
        )
        for _ in range(2):
            await FlowWorker().advance(UUID(run.run_id))
        assert (await asyncio.to_thread(sdk.get_run, run.run_id)).output == {"message": "sdk"}
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=5)
        listener.close()


async def test_fresh_engine_app_and_worker_resume_file_database(tmp_path, monkeypatch, clock):
    url = f"sqlite+aiosqlite:///{tmp_path / 'restart.sqlite'}"
    principal = MachinePrincipal(machine_id=uuid4(), key_id=uuid4(), name="restart", scopes=FLOW_SCOPES)

    async def create():
        engine = create_async_engine(url)
        maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        monkeypatch.setattr(db_engine, "get_session_maker", lambda: maker)
        app = create_app()
        app.dependency_overrides[get_flow_principal] = lambda: principal
        app.dependency_overrides[get_worker_bindings] = lambda: WorkerBindings()
        return engine, maker, app

    engine, maker, app = await create()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda connection: Base.metadata.create_all(
                    connection,
                    tables=[table for table in Base.metadata.sorted_tables if table.name.startswith("sdk_flow_")],
                )
            )
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://host") as client:
            receipt = await setup(client)
            run = await start(client)
            run = await drive(client, run, clock)
            assert run["waiting_reason"] == "approval"
    finally:
        await engine.dispose()
    engine, maker, fresh_app = await create()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(fresh_app), base_url="http://restarted") as client:
            restored = await get(client, run)
            assert restored == run
            assert restored["release_digest"] == receipt["digest"]
            approved = await command(client, restored, "approve", "after-restart")
            assert approved.status_code == 200, approved.text
            await FlowWorker(session_maker=maker).advance(UUID(run["run_id"]))
            await FlowWorker(session_maker=maker).advance(UUID(run["run_id"]))
            assert (await get(client, run))["status"] == "completed"
    finally:
        await engine.dispose()


async def test_resolved_worker_binding_is_pinned_with_release(client, owner, app, clock, session_maker):
    from app.features.execution.flows.adapters import HttpTarget

    await setup(client, release("http", "worker"))
    app.dependency_overrides[get_worker_bindings] = lambda: WorkerBindings(
        {"worker": HttpTarget(base_url="https://new-worker.test")}
    )
    # A same-content release replay must not rewrite resolved server binding.
    await client.put(RELEASE_PATH, json=release("http", "worker").model_dump(mode="json"))
    run = await start(client)
    async with session_maker() as session:
        row = await session.get(FlowRun, UUID(run["run_id"]))
        assert row.snapshot["bindings"]["planhub.prepare@1"]["base_url"] == "https://worker.test"


async def test_http_adapter_lost_response_and_cancel_tombstone(client, owner, clock, monkeypatch):
    from app.features.execution.flows.adapters import WorkerAdapter

    await setup(client, release("http", "worker"))
    store = {}
    calls = []
    first = True

    def respond(request):
        nonlocal first
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            body = json.loads(request.content)
            identity = body["attempt_id"]
            assert request.headers["idempotency-key"] == identity
            store[identity] = {"attempt_id": identity, "status": "completed", "output": body["inputs"]}
            if first:
                first = False
                raise httpx.ReadTimeout("effect succeeded, response lost")
            return httpx.Response(200, json=store[identity])
        identity = request.url.path.rsplit("/", 1)[-1]
        if request.method == "DELETE":
            store[identity] = {"attempt_id": identity, "status": "canceled"}
        return httpx.Response(200, json=store[identity])

    # Dedicated transport fixture; production adapter uses the shared getter.
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        monkeypatch.setattr("app.features.execution.flows.adapters.get_http_client", lambda: transport)
        run = await start(client)
        await FlowWorker(WorkerAdapter()).advance(UUID(run["run_id"]))
        unknown = await get(client, run)
        assert unknown["waiting_reason"] == "external-result"
        clock.advance()
        await FlowWorker().advance(UUID(run["run_id"]))
        assert [method for method, _ in calls] == ["POST", "GET"]
        assert len((await get(client, run))["attempts"]) == 1
        # A second run canceled after an unknown effect must issue worker cancellation.
        first = True
        second = await start(client, key="cancel-case")
        await FlowWorker().advance(UUID(second["run_id"]))
        waiting = await get(client, second)
        canceled = await command(client, waiting, "cancel")
        assert canceled.json()["status"] == "canceling"
        clock.advance()
        await FlowWorker().advance(UUID(second["run_id"]))
        assert (await get(client, second))["status"] == "canceled"
        assert calls[-1][0] == "DELETE"


async def test_unstructured_404_does_not_authorize_redispatch(client, owner, clock, monkeypatch):
    await setup(client, release("http", "worker"))
    calls = []

    def respond(request):
        calls.append(request.method)
        if request.method == "POST":
            raise httpx.ReadTimeout("unknown acceptance")
        return httpx.Response(404, json={"detail": "upstream route is unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        monkeypatch.setattr("app.features.execution.flows.adapters.get_http_client", lambda: transport)
        run = await start(client)
        await FlowWorker().advance(UUID(run["run_id"]))
        for _ in range(3):
            clock.advance()
            await FlowWorker().advance(UUID(run["run_id"]))
        assert calls == ["POST", "GET", "GET", "GET"]
        assert len((await get(client, run))["attempts"]) == 1
