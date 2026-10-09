"""Opt-in two-application test: installed consumer SDK talks to the actual host."""

import asyncio
import os
import socket
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
import uvicorn
from app.features.execution.flows.adapters import WorkerBindings, get_worker_bindings
from app.features.execution.flows.bridge_config import DeliveryTarget
from app.features.execution.flows.worker import FlowWorker
from app.features.project_management.pipeline_runs.models import PipelineRun
from sqlalchemy import update
from tests.integration.features.execution.flows import test_bridge as fixtures

SPEC = fixtures.SPEC
checkout = fixtures.checkout
github = fixtures.github
project = fixtures.project
paused = fixtures.paused

pytestmark = pytest.mark.real_commit


async def test_planhub_application_sdk_runs_actual_native_host(
    app, client, owner, paused, clock, session_maker, tmp_path
):
    checkout_root = os.getenv("PLANHUB_APPLICATION_TEST_ROOT")
    python = os.getenv("PLANHUB_APPLICATION_TEST_PYTHON")
    if not checkout_root or not python:
        pytest.skip("set explicit Planhub application checkout and installed Python environment")
    planhub_root = Path(checkout_root).resolve(strict=True)
    pipeline, root, head = paused
    app.dependency_overrides[get_worker_bindings] = lambda: WorkerBindings(
        deliveries={
            "local": DeliveryTarget(
                provider="planhub", environment="local", project_id=pipeline["project_id"], checkout=root
            )
        }
    )
    hub_listener = socket.socket()
    hub_listener.bind(("127.0.0.1", 0))
    hub_url = f"http://127.0.0.1:{hub_listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="error"))
    server_task = asyncio.create_task(server.serve(sockets=[hub_listener]))
    plan_listener = socket.socket()
    plan_listener.bind(("127.0.0.1", 0))
    plan_listener.listen()
    plan_url = f"http://127.0.0.1:{plan_listener.getsockname()[1]}"
    process = None
    try:
        for _ in range(300):
            if server.started:
                break
            await asyncio.sleep(0.01)
        assert server.started
        env = {
            **os.environ,
            "PYTHONPATH": str(planhub_root / "modules/hub"),
            "PLANHUB_DELIVERY_API_KEY": "test-planhub-key-at-least-32-characters",
            "PLANHUB_DELIVERY_DB": str(tmp_path / "planhub.sqlite3"),
            "PLANHUB_AUTOHUB_URL": hub_url,
            "PLANHUB_AUTOHUB_API_KEY": "test-scoped-host-key",
            "PLANHUB_AUTOHUB_PROVIDER": "planhub",
            "PLANHUB_AUTOHUB_ENVIRONMENT": "local",
            "PLANHUB_AUTOHUB_WORKER": "local",
            "PLANHUB_AUTOHUB_RELEASE_ID": "planhub-delivery-v1",
        }
        with (tmp_path / "planhub.log").open("w") as log:
            process = subprocess.Popen(
                [python, "-m", "uvicorn", "app.main:app", "--fd", str(plan_listener.fileno()), "--log-level", "error"],
                cwd=planhub_root,
                env=env,
                pass_fds=(plan_listener.fileno(),),
                stdout=log,
                stderr=log,
            )
            async with httpx.AsyncClient(
                base_url=plan_url, headers={"X-PlanHub-Key": env["PLANHUB_DELIVERY_API_KEY"]}, timeout=10
            ) as consumer:
                for _ in range(300):
                    if process.poll() is not None:
                        raise AssertionError((tmp_path / "planhub.log").read_text())
                    try:
                        if (await consumer.get("/api/health", timeout=0.2)).is_success:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.02)
                activated = await consumer.post("/api/v1/delivery/release", json={"expected_revision": 0})
                assert activated.status_code == 200, activated.text
                body = {
                    "request_id": str(uuid4()),
                    "title": "Actual application delivery",
                    "pipeline_run_id": pipeline["id"],
                    "pipeline_revision": pipeline["revision"],
                    "head_sha": head,
                    "spec_dir": SPEC,
                }
                created = await consumer.post("/api/v1/delivery/plans", json=body)
                assert created.status_code == 201, created.text
                path = f"/api/v1/delivery/plans/{created.json()['id']}"
                submitted = await consumer.post(path + "/submit")
                assert submitted.status_code == 200, submitted.text
                run_id = submitted.json()["run"]["run_id"]
                assert (await consumer.post(path + "/submit")).json()["run"]["run_id"] == run_id
                await FlowWorker().advance(UUID(run_id))
                await FlowWorker().advance(UUID(run_id))
                waiting = (await consumer.post(path + "/refresh")).json()["run"]
                assert waiting["waiting_reason"] == "approval", waiting
                approved = await consumer.post(
                    path + "/commands",
                    json={"command_id": str(uuid4()), "action": "approve", "expected_revision": waiting["revision"]},
                )
                assert approved.status_code == 200, approved.text
                await FlowWorker().advance(UUID(run_id))
                progress = (await consumer.post(path + "/refresh")).json()["run"]
                assert progress["attempts"][-1]["output"]["state"] == "awaiting_ci"
                async with session_maker() as session:
                    await session.execute(
                        update(PipelineRun).where(PipelineRun.id == UUID(pipeline["id"])).values(state="completed")
                    )
                    await session.commit()
                clock.advance()
                await FlowWorker().advance(UUID(run_id))
                await FlowWorker().advance(UUID(run_id))
                final = (await consumer.post(path + "/refresh")).json()
                assert final["run"]["status"] == "completed", final
                assert final["run"]["output"]["pipeline_run_id"] == pipeline["id"]
                assert final["pending_commands"] == []
    finally:
        if process is not None:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait)
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=5)
        hub_listener.close()
        plan_listener.close()
