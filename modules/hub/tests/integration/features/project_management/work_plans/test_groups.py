from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.features.project_management.work_plans.kick import WorkPlanKick
from tests.integration.features.project_management.work_plans.test_work_plans import create, due, get, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


@pytest.mark.parametrize("value, expected", [(None, None), (" \t ", None), (" game-a ", "game-a")])
async def test_normalization_and_legacy_update_preserves_group(client, setup_work, value, expected):
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="paused", group_key=value))
    assert plan["group_key"] == expected
    root = f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}"
    updated = await client.put(root, json=spec(expected_revision=plan["revision"]))
    assert updated.status_code == 200, updated.text
    assert updated.json()["group_key"] == expected
    cleared = await client.put(root, json=spec(expected_revision=updated.json()["revision"], group_key=" "))
    assert cleared.json()["group_key"] is None


async def test_filters_are_exact_paginated_and_project_scoped(client, setup_work):
    project, _, _, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    for key in (None, "", "game-a", "game-a", "game-ab", "(null)"):
        await create(client, project, spec(state="paused", group_key=key))
    other = (await client.post("/api/v1/projects", json={"name": "Other"})).json()
    assert (await client.get(root)).json()["total_count"] == 6
    page = (await client.get(root, params={"group_key": " game-a ", "offset": 1, "limit": 1})).json()
    assert page["total_count"] == 2 and len(page["items"]) == 1
    assert page["items"][0]["group_key"] == "game-a"
    assert (await client.get(root, params={"group_key": "", "state": "paused"})).json()["total_count"] == 2
    assert (await client.get(root, params={"group_key": "(null)"})).json()["total_count"] == 1
    assert (await client.get(root, params={"group_key": "game-a", "state": "active"})).json()["total_count"] == 0
    assert (await client.get(f"/api/v1/projects/{other['id']}/work-plans", params={"group_key": "game-a"})).json()[
        "total_count"
    ] == 0
    assert (await client.get(root, params={"group_key": "x" * 101})).status_code == 422
    assert (await client.post(root, json=spec(group_key="x" * 101))).status_code == 422


async def test_reclassification_preserves_registration_and_never_kicks_work(client, setup_work, monkeypatch):
    project, _, _, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    data = spec(request_id=str(uuid4()))
    plan = await create(client, project, data)
    kick = AsyncMock()
    monkeypatch.setattr(WorkPlanKick, "run", kick)
    body = {"group_key": "game-a", "expected_revision": plan["revision"]}
    changed = await client.patch(f"{root}/{plan['id']}/group", json=body)
    assert changed.status_code == 200, changed.text
    assert changed.json()["state"] == plan["state"]
    assert changed.json()["items"] == plan["items"]
    kick.assert_not_awaited()
    assert (await client.patch(f"{root}/{plan['id']}/group", json=body)).status_code == 409
    # An old client replay or a differently classified retry recovers; neither overwrites metadata.
    for retry in (data, data | {"group_key": "other"}):
        replay = await client.post(root, json=retry)
        assert replay.status_code == 201
        assert replay.json()["id"] == plan["id"]
        assert replay.json()["group_key"] == "game-a"
    assert (await client.post(root, json=data | {"title": "Different work"})).status_code == 409
    activity = (await client.get(f"{root}/{plan['id']}/activity")).json()
    assert activity["total_count"] == 2
    assert activity["items"][0]["changes"] == {"group_key": {"before": None, "after": "game-a"}}


@pytest.mark.parametrize("state", ["draft", "proposed", "paused", "revoked", "completed"])
async def test_group_changes_preserve_lifecycle_state(client, setup_work, session, state):
    from app.features.project_management.work_plans.models import WorkPlan

    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="paused"))
    row = await session.get(WorkPlan, UUID(plan["id"]))
    row.state = state
    await session.commit()
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}/group",
        json={"group_key": "platform", "expected_revision": plan["revision"]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["state"] == state


async def test_runs_inherit_current_group_and_cross_group_dependencies_still_execute(client, setup_work, session):
    project, github, worker, _ = setup_work
    first = await create(client, project, spec(group_key="platform", items=spec()["items"][:1]))
    second = await create(
        client, project, spec(group_key="game-a", depends_on=[first["id"]], items=spec()["items"][:1])
    )
    project_id = UUID(project["id"])
    await worker.advance_project(project_id)
    assert len(github.pulls) == 1
    run = (await get(client, project, first))["items"][0]["pipeline_run_id"]
    query = {"project_id": project["id"], "group_key": "platform"}
    listed = (await client.get("/api/v1/pipeline-runs", params=query)).json()
    assert [row["id"] for row in listed["items"]] == [run]
    current = await get(client, project, first)
    changed = await client.patch(
        f"/api/v1/projects/{project['id']}/work-plans/{first['id']}/group",
        json={"group_key": None, "expected_revision": current["revision"]},
    )
    assert changed.status_code == 200
    assert changed.json()["items"] == current["items"]
    assert (await client.get("/api/v1/pipeline-runs", params=query)).json()["total_count"] == 0
    ungrouped = (await client.get("/api/v1/pipeline-runs", params=query | {"group_key": ""})).json()
    assert [row["id"] for row in ungrouped["items"]] == [run]
    # Direct runs (without a Work Item) must also remain visible in the null view.
    from app.features.project_management.work_plans.models import WorkItem

    item = await session.get(WorkItem, UUID(current["items"][0]["id"]))
    item.pipeline_run_id = None
    await session.commit()
    assert (await client.get("/api/v1/pipeline-runs", params=query | {"group_key": ""})).json()["total_count"] == 1
    item.pipeline_run_id = UUID(run)
    await session.commit()
    github.merge(100)
    await due(session)
    await worker.advance_project(project_id)
    assert len(github.pulls) == 2
    child = await get(client, project, second)
    assert child["items"][0]["pipeline_run_id"]
    filtered = (await client.get("/api/v1/pipeline-runs", params=query | {"group_key": "game-a", "limit": 1})).json()
    assert filtered["total_count"] == 1
    assert filtered["items"][0]["id"] == child["items"][0]["pipeline_run_id"]
