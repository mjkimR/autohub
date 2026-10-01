from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.work_plans import execution_repo
from app.features.project_management.work_plans.kick import WorkPlanKick
from app.features.project_management.work_plans.models import WorkPlan
from app.features.project_management.work_plans.schemas import WorkPlanCreate
from app_testing_base import utc_now
from sqlalchemy import update
from tests.integration.features.project_management.work_plans.test_immediate_follow_up import SINGLE, lifecycle
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, due, get

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def edit(client, project, plan, scheduled_at):
    return await client.put(
        f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}",
        json=SINGLE | {"scheduled_at": scheduled_at, "expected_revision": plan["revision"]},
    )


async def test_future_schedule_gates_create_edit_resume_and_tick_until_boundary(
    client, setup_work, live_kick, monkeypatch
):
    project, github, worker, _ = setup_work
    scheduled = utc_now() + timedelta(days=1)
    plan = await create(client, project, SINGLE | {"scheduled_at": scheduled.isoformat()})
    assert datetime.fromisoformat(plan["scheduled_at"]) == scheduled
    postponed = scheduled + timedelta(hours=1)
    response = await edit(client, project, plan, postponed.isoformat())
    assert response.status_code == 200, response.text
    plan = response.json()
    plan = await control(client, project, plan, "pause")
    plan = await control(client, project, plan, "resume")
    monkeypatch.setattr(execution_repo, "get_current_utc_time", lambda: postponed - timedelta(microseconds=1))
    await worker.advance_project(UUID(project["id"]))
    assert not github.requests
    live_kick.assert_not_awaited()
    assert (await get(client, project, plan))["items"][0]["started_at"] is None

    monkeypatch.setattr(execution_repo, "get_current_utc_time", lambda: postponed)
    await worker.advance_project(UUID(project["id"]))
    started = await get(client, project, plan)
    assert started["items"][0]["state"] == "running" and len(github.pulls) == 1
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1
    assert (await edit(client, project, started, None)).status_code == 409


@pytest.mark.parametrize("scheduled_at", [None, "2020-01-01T00:00:00Z"])
async def test_removing_or_moving_reservation_to_past_starts_immediately(client, setup_work, live_kick, scheduled_at):
    project, github, _, _ = setup_work
    plan = await create(client, project, SINGLE | {"scheduled_at": (utc_now() + timedelta(days=1)).isoformat()})
    response = await edit(client, project, plan, scheduled_at)
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["state"] == "running" and len(github.pulls) == 1
    live_kick.assert_awaited_once()


@pytest.mark.parametrize("action", ["pause", "revoke"])
async def test_due_reservations_still_obey_controls(client, setup_work, live_kick, monkeypatch, action):
    project, github, worker, _ = setup_work
    scheduled = utc_now() + timedelta(days=1)
    plan = await create(client, project, SINGLE | {"scheduled_at": scheduled.isoformat()})
    plan = await control(client, project, plan, action)
    monkeypatch.setattr(execution_repo, "get_current_utc_time", lambda: scheduled)
    await worker.advance_project(UUID(project["id"]))
    assert not github.requests
    assert (await get(client, project, plan))["items"][0]["started_at"] is None
    if action == "pause":
        resumed = await control(client, project, plan, "resume")
        assert resumed["items"][0]["state"] == "running"


async def test_scheduled_plan_does_not_hold_capacity_and_webhook_cannot_start_it_early(
    client, setup_work, live_kick, monkeypatch
):
    project, github, worker, _ = setup_work
    scheduled = utc_now() + timedelta(days=1)
    reserved = await create(client, project, SINGLE | {"scheduled_at": scheduled.isoformat()})
    immediate = await create(client, project, SINGLE)
    assert len(github.pulls) == 1
    github.merge(100)
    await WorkPlanKick(lifecycle(worker)).run(
        UUID(project["id"]), run_id=UUID(immediate["items"][0]["pipeline_run_id"])
    )
    assert (await get(client, project, immediate))["state"] == "completed"
    assert (await get(client, project, reserved))["items"][0]["state"] == "waiting"
    assert len(github.pulls) == 1
    monkeypatch.setattr(execution_repo, "get_current_utc_time", lambda: scheduled)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, reserved))["items"][0]["state"] == "running"


async def test_elapsed_schedule_still_waits_for_dependencies(client, setup_work, live_kick, session):
    project, github, worker, _ = setup_work
    parent = await create(client, project, SINGLE)
    child = await create(
        client, project, SINGLE | {"scheduled_at": "2020-01-01T00:00:00Z", "depends_on": [parent["id"]]}
    )
    assert child["items"][0]["started_at"] is None and len(github.pulls) == 1
    github.merge(100)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert (await get(client, project, child))["items"][0]["state"] == "running"


async def test_schedule_requires_timezone_and_replays_equivalent_instants(client, setup_work):
    project, _, _, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    data = SINGLE | {"request_id": str(uuid4()), "scheduled_at": "2099-10-01T09:00:00+09:00"}
    invalid = await client.post(root, json=data | {"scheduled_at": "2099-10-01T09:00:00"})
    assert invalid.status_code == 422
    plan = await create(client, project, data)
    assert datetime.fromisoformat(plan["scheduled_at"]) == datetime(2099, 10, 1, tzinfo=UTC)
    replay = await client.post(root, json=data | {"scheduled_at": "2099-10-01T00:00:00Z"})
    assert replay.status_code == 201 and replay.json()["id"] == plan["id"]
    conflict = await client.post(root, json=data | {"scheduled_at": "2099-10-02T00:00:00Z"})
    assert conflict.status_code == 409


async def test_legacy_registration_digest_survives_optional_schedule(client, setup_work, session):
    project, _, _, _ = setup_work
    data = SINGLE | {"request_id": str(uuid4())}
    plan = await create(client, project, data)
    legacy = WorkPlanCreate.model_validate(data).model_dump(
        mode="json", exclude={"request_id", "scheduled_at", "state", "group_key"}
    )
    await session.execute(
        update(WorkPlan).where(WorkPlan.id == UUID(plan["id"])).values(registration_digest=request_digest(legacy))
    )
    await session.commit()
    replay = await create(client, project, data | {"scheduled_at": None})
    assert replay["id"] == plan["id"] and replay["scheduled_at"] is None
