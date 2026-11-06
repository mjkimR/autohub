import asyncio
from uuid import uuid4

import pytest
from app.features.project_management.work_plans.template_models import TemplateRequest, WorkPlanTemplate
from sqlalchemy import func, select
from tests.integration.features.project_management.work_plans.test_work_plans import create, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def root(project):
    return f"/api/v1/projects/{project['id']}/work-plan-templates"


def definition():
    return {
        "title": "Routine",
        "description": "Scope",
        "base_branch": "main",
        "items": [{"key": "a", "title": "Task", "description": "Implement", "acceptance": "Pass", "depends_on": []}],
    }


async def seed(client, setup_work):
    project = setup_work[0]
    body = {"request_id": str(uuid4()), "name": "Routine", "definition": definition()}
    response = await client.post(root(project), json=body)
    assert response.status_code == 201, response.text
    return project, response.json()["current_template"], body


def registration(project, template):
    request_id = str(uuid4())
    return {
        "request_id": request_id,
        "template_revision": template["revision"],
        "template_digest": template["digest"],
        "expected_repository": "owner/app",
        "expected_connector_id": project["github_connector_id"],
        "payload": {**definition(), "state": "draft", "request_id": request_id},
    }


async def test_template_crud_replay_and_deleted_receipt(client, setup_work):
    project, template, body = await seed(client, setup_work)
    base = root(project)
    replay = await client.post(base, json=body)
    assert replay.json()["original_template"]["id"] == template["id"]
    assert (await client.post(base, json=body | {"name": "changed"})).status_code == 409
    path = base + "/" + template["id"]
    update = body | {"request_id": str(uuid4()), "expected_revision": 1, "name": "Edited"}
    result = await client.put(path, json=update)
    assert result.status_code == 200, result.text
    assert (await client.put(path, json=update)).json()["original_template"]["revision"] == 2
    assert (await client.put(path, json=update | {"request_id": str(uuid4())})).status_code == 409
    delete = {"request_id": str(uuid4()), "expected_revision": 2}
    assert (await client.request("DELETE", path, json=delete)).status_code == 200
    assert (await client.get(path)).status_code == 404
    old = (await client.post(base, json=body)).json()
    assert old["original_template"]["revision"] == 1
    assert old["current_template"]["deleted"]
    assert (await client.get(base)).json()["total_count"] == 0
    assert (await client.get(base + "/requests/create/" + body["request_id"])).json()["original_template"][
        "id"
    ] == template["id"]
    assert (await client.get(base + "/requests/create/" + str(uuid4()))).json()["record_state"] == "unknown"


async def test_source_extracts_only_definition_and_revision_guard(client, setup_work):
    project, github, _, _ = setup_work
    plan = await create(client, project, spec(state="draft", group_key="keep-out"))
    before = len(github.requests)
    body = {
        "request_id": str(uuid4()),
        "name": "Saved source",
        "source_plan_id": plan["id"],
        "expected_revision": plan["revision"],
    }
    response = await client.post(root(project) + "/from-plan", json=body)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["source_plan_id"] == plan["id"] and result["omitted"]
    assert set(result["current_template"]["definition"]) == {"title", "description", "base_branch", "items"}
    assert "attach_branch" not in result["current_template"]["definition"]["items"][0]
    assert len(github.requests) == before
    assert (
        await client.post(
            root(project) + "/from-plan", json=body | {"request_id": str(uuid4()), "expected_revision": 999}
        )
    ).status_code == 409


async def test_registration_fresh_guards_replay_and_independence(client, setup_work):
    project, template, _body = await seed(client, setup_work)
    base = root(project)
    path = base + "/" + template["id"]
    data = registration(project, template)
    response = await client.post(path + "/registrations", json=data)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["original_plan"]["state"] == "draft"
    assert result["reviewed_payload"] == data["payload"] | {
        "group_key": None,
        "scheduled_at": None,
        "depends_on": [],
        "items": [definition()["items"][0] | {"attach_branch": None}],
    }
    await client.request("DELETE", path, json={"request_id": str(uuid4()), "expected_revision": 1})
    replay = await client.post(path + "/registrations", json=data)
    assert replay.status_code == 201, replay.text
    assert replay.json()["original_plan"]["id"] == result["original_plan"]["id"]
    assert replay.json()["current_template"]["deleted"]
    assert (
        await client.post(path + "/registrations", json=data | {"expected_repository": "changed/repo"})
    ).status_code == 409
    assert (await client.post(path + "/registrations", json=registration(project, template))).status_code == 404
    lookup = await client.get(base + "/registrations/" + data["request_id"])
    assert lookup.json()["original_template"]["definition"] == template["definition"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("template_revision", 99),
        ("template_digest", "0" * 64),
        ("expected_repository", "foreign/repo"),
        ("expected_connector_id", "00000000-0000-0000-0000-000000000001"),
    ],
)
async def test_stale_template_binding_refuses_without_plan(client, setup_work, session, field, value):
    project, template, _ = await seed(client, setup_work)
    response = await client.post(
        root(project) + "/" + template["id"] + "/registrations", json=registration(project, template) | {field: value}
    )
    assert response.status_code == 409, response.text
    from app.features.project_management.work_plans.models import WorkPlan

    assert await session.scalar(select(func.count()).select_from(WorkPlan)) == 0


async def test_strict_definition_path_actor_and_ordinary_collision(client, setup_work):
    project, template, body = await seed(client, setup_work)
    base = root(project)
    assert (await client.post(base, json=body | {"actor": "spoof"})).status_code == 422
    invalid = definition() | {"items": [definition()["items"][0] | {"attach_branch": "dev-other"}]}
    assert (await client.post(base, json=body | {"request_id": str(uuid4()), "definition": invalid})).status_code == 422
    assert (await client.put(base + "/" + str(uuid4()), json=body | {"expected_revision": 1})).status_code == 404
    data = registration(project, template)
    await create(client, project, data["payload"])
    assert (await client.post(base + "/" + template["id"] + "/registrations", json=data)).status_code == 409


async def test_receipt_failure_rolls_back_template(client, setup_work, session, monkeypatch):
    project = setup_work[0]
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    def fail(_session, _context, _instances):
        if any(isinstance(row, TemplateRequest) for row in _session.new):
            raise RuntimeError("receipt failure")

    event.listen(Session, "before_flush", fail)
    try:
        with pytest.raises(RuntimeError, match="receipt failure"):
            await client.post(
                root(project), json={"request_id": str(uuid4()), "name": "Rollback", "definition": definition()}
            )
    finally:
        event.remove(Session, "before_flush", fail)
    assert await session.scalar(select(func.count()).select_from(WorkPlanTemplate)) == 0


@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_registration_serializes_template_change(client, setup_work, session, operation):
    if session.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL row locks")
    project, template, body = await seed(client, setup_work)
    data = registration(project, template)
    path = root(project) + "/" + template["id"]
    barrier = asyncio.Event()

    async def change():
        await barrier.wait()
        if operation == "delete":
            return await client.request("DELETE", path, json={"request_id": str(uuid4()), "expected_revision": 1})
        return await client.put(path, json=body | {"request_id": str(uuid4()), "expected_revision": 1})

    async def register():
        await barrier.wait()
        return await client.post(path + "/registrations", json=data)

    tasks = [asyncio.create_task(change()), asyncio.create_task(register())]
    barrier.set()
    results = await asyncio.gather(*tasks)
    assert results[0].status_code == 200
    assert results[1].status_code in (201, 404, 409)
    replay = await client.post(path + "/registrations", json=data)
    assert replay.status_code == results[1].status_code
    if replay.status_code == 201:
        assert replay.json()["original_plan"]["id"] == results[1].json()["original_plan"]["id"]


async def test_actor_and_target_bound_replay(client, setup_work, session):
    project, template, body = await seed(client, setup_work)
    from sqlalchemy import update

    await session.execute(update(TemplateRequest).values(actor="user:another"))
    await session.commit()
    assert (await client.post(root(project), json=body)).status_code == 409
    update_body = body | {"request_id": str(uuid4()), "expected_revision": 1}
    first = await client.put(root(project) + "/" + template["id"], json=update_body)
    assert first.status_code == 200
    assert (await client.put(root(project) + "/" + str(uuid4()), json=update_body)).status_code == 409


async def test_registration_receipt_failure_rolls_back_plan(client, setup_work, session):
    project, template, _ = await seed(client, setup_work)
    from app.features.project_management.work_plans.models import WorkPlan
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    def fail(_session, _context, _instances):
        if any(isinstance(row, TemplateRequest) and row.operation == "register" for row in _session.new):
            raise RuntimeError("registration receipt failed")

    event.listen(Session, "before_flush", fail)
    try:
        with pytest.raises(RuntimeError, match="registration receipt failed"):
            await client.post(
                root(project) + "/" + template["id"] + "/registrations", json=registration(project, template)
            )
    finally:
        event.remove(Session, "before_flush", fail)
    assert await session.scalar(select(func.count()).select_from(WorkPlan)) == 0


async def test_post_commit_admission_failure_keeps_recorded_result(client, setup_work, monkeypatch):
    from app.features.project_management.work_plans.kick import WorkPlanKick

    project, template, _ = await seed(client, setup_work)
    data = registration(project, template)
    data["payload"]["state"] = "active"
    calls = []

    async def fail(self, project_id):
        calls.append(project_id)
        raise RuntimeError("after commit")

    monkeypatch.setattr(WorkPlanKick, "run", fail)
    path = root(project) + "/" + template["id"] + "/registrations"
    result = await client.post(path, json=data)
    assert result.status_code == 201, result.text
    assert result.json()["refresh_error"]
    replay = await client.post(path, json=data)
    assert replay.json()["original_plan"]["id"] == result.json()["original_plan"]["id"]
    assert len(calls) == 1
