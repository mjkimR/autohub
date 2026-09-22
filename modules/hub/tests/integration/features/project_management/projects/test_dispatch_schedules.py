from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.features.scheduling.schedule_configs.models import ScheduleConfig
from app_testing_base import utc_now

from tests.integration.features.project_management.projects.test_projects_api import (
    github_connector as github_connector,
)
from tests.integration.features.project_management.projects.test_projects_api import (
    github_scenario as github_scenario,
)
from tests.integration.features.project_management.projects.test_projects_api import (
    project_payload as project_payload,
)
from tests.utils.assertions import assert_status_code

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def dispatches(client, project_id):
    rows = (await client.get("/api/v1/schedule_configs")).json()["items"]
    return [
        r
        for r in rows
        if r["task_func"] == "pipeline.dispatch_project" and r["payload"].get("project_id") == project_id
    ]


@pytest.mark.parametrize("enabled", [True, False])
async def test_later_github_connection_creates_one_dispatcher(client, project_payload, enabled):
    created = await client.post("/api/v1/projects", json={"name": "Application", "enabled": enabled})
    assert_status_code(created, 201)
    project = created.json()
    assert await dispatches(client, project["id"]) == []

    for _ in range(2):
        updated = await client.put(
            f"/api/v1/projects/{project['id']}",
            json={**project_payload, "enabled": enabled, "expected_revision": project["revision"]},
        )
        assert_status_code(updated, 200)
        project = updated.json()
        [schedule] = await dispatches(client, project["id"])
        assert schedule["enabled"] is enabled
        assert schedule["interval_seconds"] == 60
        if _ == 0:
            first = schedule
        else:
            assert schedule["id"] == first["id"]
            assert schedule["next_run_at"] == first["next_run_at"]


async def test_project_save_repairs_a_missing_dispatcher(client, session, project_payload):
    project = (await client.post("/api/v1/projects", json=project_payload)).json()
    [previous] = await dispatches(client, project["id"])
    config = await session.get(ScheduleConfig, UUID(previous["id"]))
    await session.delete(config)
    await session.commit()

    updated = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={**project_payload, "expected_revision": project["revision"]},
    )
    assert_status_code(updated, 200)
    [repaired] = await dispatches(client, project["id"])
    assert repaired["id"] != previous["id"]
    assert repaired["enabled"] is True


async def test_disconnect_pauses_dispatch_and_reconnect_preserves_history(client, session, project_payload):
    project = (await client.post("/api/v1/projects", json=project_payload)).json()
    [initial] = await dispatches(client, project["id"])
    last_run = utc_now() - timedelta(days=1)
    config = await session.get(ScheduleConfig, UUID(initial["id"]))
    config.last_run_at = last_run
    config.next_run_at = last_run
    await session.commit()

    disconnected = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={"name": project["name"], "github": None, "expected_revision": project["revision"]},
    )
    assert_status_code(disconnected, 200)
    [paused] = await dispatches(client, project["id"])
    assert paused["id"] == initial["id"] and paused["enabled"] is False

    before_reconnect = utc_now()
    reconnected = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={**project_payload, "expected_revision": disconnected.json()["revision"]},
    )
    assert_status_code(reconnected, 200)
    [active] = await dispatches(client, project["id"])
    assert active["id"] == initial["id"] and active["enabled"] is True
    assert active["last_run_at"] == paused["last_run_at"]
    assert datetime.fromisoformat(active["next_run_at"]).replace(tzinfo=UTC) >= before_reconnect + timedelta(seconds=60)


async def test_dispatch_cadence_controls_first_run_and_changes(client, project_payload):
    before_create = utc_now()
    project = (
        await client.post(
            "/api/v1/projects", json={**project_payload, "automation": {"dispatch_interval_seconds": 300}}
        )
    ).json()
    [initial] = await dispatches(client, project["id"])
    assert datetime.fromisoformat(initial["next_run_at"]).replace(tzinfo=UTC) >= before_create + timedelta(seconds=300)

    before_update = utc_now()
    changed = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={
            **project_payload,
            "automation": {"dispatch_interval_seconds": 120},
            "expected_revision": project["revision"],
        },
    )
    assert_status_code(changed, 200)
    [updated] = await dispatches(client, project["id"])
    assert updated["id"] == initial["id"]
    assert updated["interval_seconds"] == 120
    assert (
        before_update + timedelta(seconds=120)
        <= datetime.fromisoformat(updated["next_run_at"]).replace(tzinfo=UTC)
        < before_update + timedelta(seconds=130)
    )


async def test_generic_api_cannot_mutate_or_duplicate_project_dispatch(client, project_payload):
    project = (await client.post("/api/v1/projects", json=project_payload)).json()
    [schedule] = await dispatches(client, project["id"])
    path = f"/api/v1/schedule_configs/{schedule['id']}"
    replacement = {"name": "Bypass", "task_func": "hello_world", "interval_seconds": 120, "payload": {}}
    for response in [
        await client.patch(path, json={"enabled": False}),
        await client.put(path, json=replacement),
        await client.delete(path),
        await client.post(
            "/api/v1/schedule_configs",
            json={**replacement, "task_func": "pipeline.dispatch_project", "payload": {"project_id": project["id"]}},
        ),
    ]:
        assert_status_code(response, 409)
        assert "managed by a project" in response.json()["detail"]
    assert (await client.get(path)).json() == schedule
    assert len(await dispatches(client, project["id"])) == 1

    ordinary = await client.post("/api/v1/schedule_configs", json=replacement)
    assert_status_code(ordinary, 201)
    ordinary_path = f"/api/v1/schedule_configs/{ordinary.json()['id']}"
    for response in [
        await client.patch(ordinary_path, json={"task_func": "pipeline.dispatch_project"}),
        await client.put(ordinary_path, json={**replacement, "task_func": "pipeline.dispatch_project"}),
    ]:
        assert_status_code(response, 409)
    assert (await client.get(ordinary_path)).json()["task_func"] == "hello_world"
    assert_status_code(await client.delete(ordinary_path), 200)
    assert_status_code(await client.delete(f"/api/v1/projects/{project['id']}"), 204)
    assert await dispatches(client, project["id"]) == []
