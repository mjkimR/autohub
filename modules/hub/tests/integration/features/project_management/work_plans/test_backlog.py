import asyncio
from uuid import UUID, uuid4

import pytest
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, due, get, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def endpoint(project, plan=None):
    root = f"/api/v1/projects/{project['id']}/work-plans"
    return root if plan is None else root + f"/{plan['id']}"


@pytest.mark.parametrize("mutation", ["update", "pause"])
@pytest.mark.parametrize("reason", ["", "Hold until product review"])
async def test_unchanged_mutations_record_accepted_revision_and_reason(client, setup_work, mutation, reason):
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="draft" if mutation == "update" else "paused"))
    path = endpoint(project, plan)

    async def mutate():
        if mutation == "update":
            return await client.put(path, json=spec(expected_revision=1, reason=reason))
        return await client.post(path + "/control", json={"action": "pause", "expected_revision": 1, "reason": reason})

    response = await mutate()
    assert response.status_code == 200, response.text
    assert response.json()["revision"] == 2
    assert response.json()["state"] == plan["state"]
    history = (await client.get(path + "/activity")).json()
    assert history["total_count"] == 2
    event = next(row for row in history["items"] if row["revision"] == 2)
    assert event["body"] == reason and event["changes"] == {}
    assert event["actor"].startswith("user:")
    assert event["kind"] == ("updated" if mutation == "update" else "control")
    assert (await mutate()).status_code == 409
    assert (await client.get(path + "/activity")).json()["total_count"] == 2


@pytest.mark.parametrize("state", ["draft", "proposed", "paused"])
async def test_nonactive_registration_never_admits(client, setup_work, live_kick, state):
    project, github, worker, mirror = setup_work
    plan = await create(client, project, spec(state=state, scheduled_at="2020-01-01T00:00:00Z"))
    await worker.advance_project(UUID(project["id"]))
    await mirror.execute()
    assert not github.pulls
    assert all(item["started_at"] is None for item in (await get(client, project, plan))["items"])
    live_kick.assert_not_awaited()
    if state != "paused":
        assert github.requests == []
        assert plan["issue"] is None


async def test_seed_requires_explicit_validated_transition_and_preserves_replay(client, setup_work, live_kick):
    project, github, _, _ = setup_work
    data = {"title": "Seed", "state": "draft", "request_id": str(uuid4())}
    plan = await create(client, project, data)
    path = endpoint(project, plan)
    assert plan["items"] == []
    for action in ("propose", "ready", "resume"):
        result = await client.post(path + "/control", json={"action": action, "expected_revision": plan["revision"]})
        assert result.status_code == 422, result.text
    assert (await client.post(path + "/control", json={"action": "pause", "expected_revision": 1})).status_code == 409
    assert (await client.get(path + "/activity")).json()["total_count"] == 1
    partial = await client.put(path, json={"title": "Seed", "items": [{"key": "a"}], "expected_revision": 1})
    assert partial.status_code == 200, partial.text
    assert partial.json()["state"] == "draft"
    invalid = await client.post(path + "/control", json={"action": "propose", "expected_revision": 2})
    assert invalid.status_code == 422
    ready = await client.put(path, json=spec(expected_revision=2, reason="Refined in conversation"))
    assert ready.status_code == 200, ready.text
    proposed = await control(client, project, ready.json(), "propose")
    assert proposed["state"] == "proposed"
    replay = await create(client, project, data)
    assert replay["state"] == "proposed" and replay["revision"] == proposed["revision"]
    assert github.requests == []
    saved = await control(client, project, proposed, "ready")
    assert saved["state"] == "paused"
    assert not github.pulls
    running = await control(client, project, saved, "resume")
    assert running["items"][0]["started_at"] is not None
    assert len(github.pulls) == 1


async def test_proposed_edit_returns_to_draft_and_membership_history_is_durable(client, setup_work):
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="proposed"))
    path = endpoint(project, plan)
    old_id = plan["items"][0]["id"]
    changed = await client.put(path, json=spec(items=[spec()["items"][0], {"key": "new"}], expected_revision=1))
    assert changed.status_code == 200, changed.text
    current = changed.json()
    assert current["state"] == "draft"
    assert current["items"][0]["id"] == old_id
    assert [item["key"] for item in current["items"]] == ["a", "new"]
    history = (await client.get(path + "/activity")).json()
    edit = next(row for row in history["items"] if row["kind"] == "updated")
    assert edit["actor"].startswith("user:")
    assert edit["changes"]["state"] == {"before": "proposed", "after": "draft"}
    assert [row["key"] for row in edit["changes"]["items"]["before"]] == ["a", "b"]
    assert [row["key"] for row in edit["changes"]["items"]["after"]] == ["a", "new"]
    stale = await client.put(path, json=spec(expected_revision=1))
    assert stale.status_code == 409
    assert (await client.get(path + "/activity")).json()["total_count"] == 2
    emptied = await client.put(path, json=spec(items=[], expected_revision=2))
    assert emptied.status_code == 200 and emptied.json()["items"] == []


async def test_invalid_graph_rolls_back_and_ready_membership_stays_fixed(client, setup_work):
    project, _, _, _ = setup_work
    draft = await create(client, project, spec(state="draft"))
    path = endpoint(project, draft)
    invalid = await client.put(path, json=spec(items=[{"key": "b", "depends_on": ["a"]}], expected_revision=1))
    assert invalid.status_code == 422
    assert (await get(client, project, draft))["revision"] == 1
    assert (await client.get(path + "/activity")).json()["total_count"] == 1
    ready = await control(client, project, draft, "ready")
    assert (
        await client.post(path + "/control", json={"action": "draft", "expected_revision": ready["revision"]})
    ).status_code == 409
    invalid = await client.put(path, json=spec(items=[], expected_revision=ready["revision"]))
    assert invalid.status_code == 422
    invalid = await client.put(path, json=spec(items=[spec()["items"][0]], expected_revision=ready["revision"]))
    assert invalid.status_code == 422


async def test_comments_are_idempotent_context_only_and_activity_is_paged(client, setup_work, live_kick):
    project, github, _, _ = setup_work
    plan = await create(client, project, {"title": "Seed", "state": "draft"})
    path = endpoint(project, plan)
    data = {"request_id": str(uuid4()), "body": "Please start this immediately"}
    first = await client.post(path + "/comments", json=data)
    assert first.status_code == 201, first.text
    assert first.json()["actor"].startswith("user:")
    assert first.json()["created_at"].endswith("Z")
    assert (await client.post(path + "/comments", json=data)).json()["id"] == first.json()["id"]
    assert (await client.post(path + "/comments", json=data | {"body": "Changed"})).status_code == 409
    assert (await client.post(path + "/comments", json=data | {"actor": "user:someone"})).status_code == 422
    for i in range(3):
        assert (
            await client.post(path + "/comments", json={"request_id": str(uuid4()), "body": f"Context {i}"})
        ).status_code == 201
    first_page = (await client.get(path + "/activity?limit=2")).json()
    rest = (await client.get(path + "/activity?offset=2&limit=10")).json()
    assert first_page["total_count"] == 5
    assert len({row["id"] for row in first_page["items"] + rest["items"]}) == 5
    comments = (await client.get(path + "/activity?comments_only=true")).json()
    assert comments["total_count"] == 4
    assert all(row["kind"] == "comment" for row in comments["items"])
    assert (await get(client, project, plan))["revision"] == 1
    assert github.requests == []
    live_kick.assert_not_awaited()
    wrong_project = path.replace(project["id"], str(uuid4()))
    assert (await client.get(wrong_project + "/activity")).status_code == 404
    assert (await client.post(wrong_project + "/comments", json=data)).status_code == 404


async def test_draft_filter_withdrawal_and_revocation_do_not_publish(client, setup_work):
    project, github, _, mirror = setup_work
    draft = await create(client, project, spec(state="draft"))
    proposed = await create(client, project, spec(state="proposed"))
    filtered = (await client.get(endpoint(project) + "?state=proposed")).json()
    assert filtered["total_count"] == 1 and filtered["items"][0]["id"] == proposed["id"]
    withdrawn = await control(client, project, proposed, "draft")
    assert withdrawn["state"] == "draft"
    await control(client, project, draft, "revoke")
    await mirror.execute()
    assert not github.issues


async def test_automatic_completion_has_system_history(client, setup_work, session):
    project, github, worker, _ = setup_work
    plan = await create(client, project, spec(items=[spec()["items"][0]]))
    await worker.advance_project(UUID(project["id"]))
    github.merge(100)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    history = (await client.get(endpoint(project, plan) + "/activity")).json()
    event = next(row for row in history["items"] if row["kind"] == "completed")
    assert event["actor"] == "system:work-execution"
    assert event["changes"]["state"]["after"] == "completed"


async def test_concurrent_comment_and_transition_retries(client, setup_work, is_postgres):
    if not is_postgres:
        pytest.skip("Requires PostgreSQL row locks")
    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="draft"))
    path = endpoint(project, plan)
    data = {"request_id": str(uuid4()), "body": "Concurrent comment"}
    responses = await asyncio.gather(*(client.post(path + "/comments", json=data) for _ in range(3)))
    assert all(row.status_code == 201 for row in responses)
    assert len({row.json()["id"] for row in responses}) == 1
    responses = await asyncio.gather(
        *(
            client.post(path + "/control", json={"action": action, "expected_revision": 1})
            for action in ("propose", "ready")
        )
    )
    assert sorted(row.status_code for row in responses) == [200, 409]
    assert (await client.get(path + "/activity")).json()["total_count"] == 3


async def test_audit_failure_rolls_back_plan_edit(client, setup_work, monkeypatch):
    from unittest.mock import AsyncMock

    from app.features.project_management.projects.repos import ProjectRepository
    from app.features.project_management.projects.services import ProjectService
    from app.features.project_management.work_plans import services
    from app.features.project_management.work_plans.repos import WorkPlanRepository
    from app.features.project_management.work_plans.schemas import WorkPlanUpdate
    from app.features.project_management.work_plans.usecases import WorkPlanUseCase

    project, _, _, _ = setup_work
    plan = await create(client, project, spec(state="draft"))
    use_case = WorkPlanUseCase(
        services.WorkPlanService(WorkPlanRepository(), ProjectService(ProjectRepository())), AsyncMock()
    )
    monkeypatch.setattr(services, "record_change", AsyncMock(side_effect=RuntimeError("Audit storage unavailable")))
    with pytest.raises(RuntimeError, match="Audit storage unavailable"):
        await use_case.update(
            UUID(project["id"]),
            UUID(plan["id"]),
            WorkPlanUpdate(**spec(title="Unsaved change", items=[], expected_revision=1)),
        )
    current = await get(client, project, plan)
    assert current["title"] == plan["title"] and current["revision"] == 1
    assert len(current["items"]) == 2
    assert (await client.get(endpoint(project, plan) + "/activity")).json()["total_count"] == 1


async def test_plan_cannot_be_activated_after_repository_rebinding(client, setup_work, session):
    from app.features.project_management.projects.models import Project
    from sqlalchemy import update

    project, github, _, _ = setup_work
    plan = await create(client, project, spec(state="draft"))
    await session.execute(
        update(Project).where(Project.id == UUID(project["id"])).values(github_repository="owner/other")
    )
    await session.commit()
    response = await client.post(
        endpoint(project, plan) + "/control", json={"action": "resume", "expected_revision": 1}
    )
    assert response.status_code == 409
    assert (await get(client, project, plan))["state"] == "draft"
    assert github.requests == []


@pytest.mark.parametrize("state", ["draft", "proposed"])
async def test_complete_backlog_can_start_directly(client, setup_work, live_kick, state):
    project, github, _, _ = setup_work
    plan = await create(client, project, spec(state=state))
    running = await control(client, project, plan, "resume")
    assert running["state"] == "active" and len(github.pulls) == 1


async def test_draft_edit_races_with_activation(client, setup_work, is_postgres):
    if not is_postgres:
        pytest.skip("Requires PostgreSQL row locks")
    project, github, worker, _ = setup_work
    plan = await create(client, project, spec(state="draft"))
    path = endpoint(project, plan)
    edited, activated = await asyncio.gather(
        client.put(path, json=spec(title="Changed seed", items=[], expected_revision=1)),
        client.post(path + "/control", json={"action": "resume", "expected_revision": 1}),
    )
    assert sorted([edited.status_code, activated.status_code]) == [200, 409]
    await worker.advance_project(UUID(project["id"]))
    current = await get(client, project, plan)
    if edited.status_code == 200:
        assert current["state"] == "draft" and not current["items"] and not github.pulls
    else:
        assert current["state"] == "active" and current["title"] == plan["title"] and len(github.pulls) == 1
