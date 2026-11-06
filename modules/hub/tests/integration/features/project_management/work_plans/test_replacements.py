import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from app.features.project_management.work_plans.execution_repo import WorkExecutionRepository
from app.features.project_management.work_plans.models import WorkItem, WorkPlan
from app.features.project_management.work_plans.replacement_models import (
    ReplacementAcceptance,
    ReplacementEvent,
    ReplacementLink,
)
from app_testing_base import utc_now
from sqlalchemy import func, select
from tests.integration.features.project_management.work_plans.test_work_plans import control, create, due, get, spec

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def path(project, plan, item):
    return f"/api/v1/projects/{project['id']}/work-plans/{plan['id']}/items/{item['id']}/replacement-links"


def command(read, other):
    return dict(
        request_id=str(uuid4()),
        reason="Reviewed equivalent work",
        expected_original_revision=read["original"]["plan_revision"],
        expected_replacement_revision=other["plan_revision"],
        expected_evidence_revision=read["evidence_revision"],
    )


async def fixture(client, setup_work, session):
    project, github, worker, _ = setup_work
    original = await create(client, project, spec(items=[*spec()["items"], {**spec()["items"][1], "key": "c"}]))
    github.refs.pop("main")
    await worker.advance_project(UUID(project["id"]))
    github.refs["main"] = "a" * 40
    original = await get(client, project, original)
    a = original["items"][0]
    assert a["state"] == "preparation_failed"
    replacement = await create(
        client, project, spec(title="Replacement", items=[{**spec()["items"][0], "key": "replacement"}])
    )
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    github.merge(100)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    replacement = await get(client, project, replacement)
    r = replacement["items"][0]
    assert r["state"] == "succeeded"
    root = path(project, original, a)
    read = (await client.get(root, params={"replacement_item_id": r["id"]})).json()
    data = command(read, read["candidate"]) | {"replacement_item_id": r["id"]}
    linked = await client.post(root, json=data)
    assert linked.status_code == 200, linked.text
    return project, github, worker, original, replacement, root, linked.json(), data


def accept_command(read, dependent):
    r = read["links"][-1]["current_replacement"]
    return command(read, r) | dict(
        dependent_item_id=dependent["id"],
        original_digest=read["original"]["digest"],
        replacement_digest=r["digest"],
        merge_sha=r["merge_sha"],
        execution_id=r["execution_id"],
    )


async def accept(client, root, read, dependent):
    endpoint = root + "/" + read["links"][-1]["id"] + "/acceptances"
    data = accept_command(read, dependent)
    response = await client.post(endpoint, json=data)
    assert response.status_code == 200, response.text
    return response.json(), endpoint, data


async def test_exact_edge_release_consumption_and_replay(client, setup_work, session):
    project, github, worker, original, replacement, root, read, _data = await fixture(client, setup_work, session)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1  # linking and successful replacement do nothing
    accepted, endpoint, body = await accept(client, root, read, original["items"][1])
    before = await session.scalar(select(func.count()).select_from(ReplacementEvent))
    assert (await client.post(endpoint, json=body)).json()["result"] == accepted["result"]
    assert (await client.post(endpoint, json=body | {"reason": "changed"})).status_code == 409
    assert (await client.post(endpoint, json=body | {"actor": "spoof"})).status_code == 422
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    current = await get(client, project, original)
    assert [i["state"] for i in current["items"]] == ["preparation_failed", "running", "waiting"]
    final = (await client.get(root)).json()
    assert final["links"][0]["acceptances"][0]["consumed"]
    withdraw = command(final, final["links"][0]["current_replacement"])
    assert (await client.post(root + "/" + read["links"][0]["id"] + "/withdraw", json=withdraw)).status_code == 409
    assert (await client.post(endpoint, json=body)).json()["result"] == accepted["result"]
    assert await session.scalar(select(func.count()).select_from(ReplacementEvent)) == before + 1
    assert final["original"]["item_state"] == "preparation_failed"
    assert replacement["items"][0]["pipeline_run_id"] != current["items"][1]["pipeline_run_id"]


async def test_unconsumed_withdraw_and_historical_endpoint_roles(client, setup_work, session):
    project, _, _, original, replacement, root, read, _data = await fixture(client, setup_work, session)
    accepted, _, _ = await accept(client, root, read, original["items"][1])
    aid = accepted["result"]["acceptance_id"]
    lid = read["links"][0]["id"]
    cmd = command(accepted, accepted["links"][0]["current_replacement"]) | {"acceptance_id": aid}
    withdrawn = await client.post(root + "/" + lid + "/withdraw", json=cmd)
    assert withdrawn.status_code == 200, withdrawn.text
    again, _, _ = await accept(client, root, withdrawn.json(), original["items"][1])
    cmd = command(again, again["links"][0]["current_replacement"])
    withdrawn = await client.post(root + "/" + lid + "/withdraw", json=cmd)
    assert withdrawn.status_code == 200
    assert all(not a["active"] for a in withdrawn.json()["links"][0]["acceptances"])
    fresh = command(withdrawn.json(), withdrawn.json()["links"][0]["current_replacement"]) | {
        "replacement_item_id": replacement["items"][0]["id"]
    }
    assert (await client.post(root, json=fresh)).status_code == 409
    # A different candidate remains permitted after permanent pair withdrawal.
    second = await create(client, project, spec(state="paused", items=[{**spec()["items"][0], "key": "r2"}]))
    r = (await client.get(root, params={"replacement_item_id": second["items"][0]["id"]})).json()
    assert (
        await client.post(root, json=command(r, r["candidate"]) | {"replacement_item_id": second["items"][0]["id"]})
    ).status_code == 200


@pytest.mark.parametrize("mutation", ["digest", "merge", "execution", "revision", "missing_edge"])
async def test_acceptance_rejects_changed_review(client, setup_work, session, mutation):
    _, _, _, original, _, root, read, _ = await fixture(client, setup_work, session)
    body = accept_command(read, original["items"][1])
    key, value = {
        "digest": ("original_digest", "x"),
        "merge": ("merge_sha", "x"),
        "execution": ("execution_id", str(uuid4())),
        "revision": ("expected_evidence_revision", 99),
        "missing_edge": ("dependent_item_id", original["items"][0]["id"]),
    }[mutation]
    response = await client.post(root + "/" + read["links"][0]["id"] + "/acceptances", json=body | {key: value})
    assert response.status_code == 409, response.text
    assert await session.scalar(select(func.count()).select_from(ReplacementAcceptance)) == 0


async def test_merge_snapshot_retains_after_pruning_and_other_holds(client, setup_work, session):
    project, github, worker, original, replacement, root, read, _ = await fixture(client, setup_work, session)
    r = await session.get(WorkItem, UUID(replacement["items"][0]["id"]))
    r.pipeline_run_id = None
    r.pipeline_run_retired_at = utc_now()
    plan = await session.get(WorkPlan, UUID(original["id"]))
    plan.scheduled_at = utc_now() + timedelta(days=1)
    await session.commit()
    read = (await client.get(root)).json()
    accepted, _, _ = await accept(client, root, read, original["items"][1])
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1
    assert not accepted["links"][0]["acceptances"][0]["consumed"]
    plan = await session.get(WorkPlan, UUID(original["id"]), populate_existing=True)
    plan.state = "paused"
    plan.scheduled_at = None
    await session.commit()
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1


async def test_activity_failure_rolls_back_acceptance(client, setup_work, session, monkeypatch):
    from app.features.project_management.work_plans import replacement_usecase

    _, _, _, original, _, root, read, _ = await fixture(client, setup_work, session)
    monkeypatch.setattr(
        replacement_usecase, "record_change", AsyncMock(side_effect=RuntimeError("activity unavailable"))
    )
    with pytest.raises(RuntimeError, match="activity unavailable"):
        await client.post(
            root + "/" + read["links"][0]["id"] + "/acceptances", json=accept_command(read, original["items"][1])
        )
    assert await session.scalar(select(func.count()).select_from(ReplacementAcceptance)) == 0
    assert (await client.get(root)).json()["evidence_revision"] == read["evidence_revision"]


async def test_revoked_original_is_supported_without_reviving_plan(client, setup_work, session):
    project, _, _, _ = setup_work
    original = await create(client, project, spec(state="paused"))
    original = await control(client, project, original, "revoke")
    replacement = await create(client, project, spec(state="paused"))
    root = path(project, original, original["items"][0])
    read = (await client.get(root, params={"replacement_item_id": replacement["items"][0]["id"]})).json()
    response = await client.post(
        root, json=command(read, read["candidate"]) | {"replacement_item_id": replacement["items"][0]["id"]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["original"]["plan_state"] == "revoked"
    assert response.json()["original"]["item_state"] == "revoked"


async def test_competing_link_requests_are_project_serialized_postgres(client, setup_work, session, monkeypatch):
    if session.bind.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    from app.features.project_management.projects.repos import ProjectRepository

    _, _, _, _, _, root, read, _ = await fixture(client, setup_work, session)
    # Withdraw the fixture link and race distinct, unused replacement endpoints.
    lid = read["links"][0]["id"]
    _withdrawn = (
        await client.post(root + "/" + lid + "/withdraw", json=command(read, read["links"][0]["current_replacement"]))
    ).json()
    project = setup_work[0]
    candidates = [
        await create(client, project, spec(state="paused", items=[{**spec()["items"][0], "key": f"r{i}"}]))
        for i in range(2)
    ]
    commands = []
    for candidate in candidates:
        review = (await client.get(root, params={"replacement_item_id": candidate["items"][0]["id"]})).json()
        commands.append(command(review, review["candidate"]) | {"replacement_item_id": candidate["items"][0]["id"]})
    old = ProjectRepository.get
    reached = 0
    barrier = asyncio.Event()

    async def get_project(self, *args, **kwargs):
        nonlocal reached
        if kwargs.get("lock"):
            reached += 1
            if reached == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), 5)
        return await old(self, *args, **kwargs)

    monkeypatch.setattr(ProjectRepository, "get", get_project)
    responses = await asyncio.gather(*(client.post(root, json=data) for data in commands))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert (
        await session.scalar(select(func.count()).select_from(ReplacementLink).where(ReplacementLink.active.is_(True)))
        == 1
    )


@pytest.mark.parametrize("racer", ["withdraw", "pause", "revoke", "recover"])
async def test_admission_races_controls_withdrawal_and_recovery_postgres(
    client, setup_work, session, monkeypatch, racer
):
    if session.bind.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    from app.features.project_management.projects.repos import ProjectRepository
    from app_layer_base.core.database.transaction import AsyncTransaction

    project, _, _, original, _, root, read, _ = await fixture(client, setup_work, session)
    accepted, _, _ = await accept(client, root, read, original["items"][1])
    old = ProjectRepository.get
    reached = 0
    barrier = asyncio.Event()

    async def get_project(self, *args, **kwargs):
        nonlocal reached
        if kwargs.get("lock"):
            reached += 1
            if reached == 2:
                barrier.set()
            await asyncio.wait_for(barrier.wait(), 5)
        return await old(self, *args, **kwargs)

    monkeypatch.setattr(ProjectRepository, "get", get_project)

    async def admit():
        async with AsyncTransaction() as tx:
            return await WorkExecutionRepository().claim(tx, UUID(project["id"]), phase="admit")

    if racer == "withdraw":
        mutation = client.post(
            root + "/" + accepted["links"][0]["id"] + "/withdraw",
            json=command(accepted, accepted["links"][0]["current_replacement"]),
        )
    elif racer == "recover":
        mutation = client.post(
            root.removesuffix("/replacement-links") + "/recover",
            json={
                "request_id": str(uuid4()),
                "expected_revision": accepted["original"]["plan_revision"],
                "reason": "Retry original",
            },
        )
    else:
        mutation = client.post(
            f"/api/v1/projects/{project['id']}/work-plans/{original['id']}/control",
            json={"expected_revision": accepted["original"]["plan_revision"], "action": racer},
        )
    claimed, response = await asyncio.gather(admit(), mutation)
    assert response.status_code in (200, 409), response.text
    after = (await client.get(root)).json()
    consumed = after["links"][0]["acceptances"][0]["consumed"]
    if racer == "withdraw":
        assert (response.status_code == 409 and consumed and claimed is not None) or (
            response.status_code == 200 and not consumed and claimed is None
        )
    elif racer in ("pause", "revoke") and response.status_code == 200:
        if claimed is None:
            assert not consumed
        else:
            assert consumed and claimed[1].state == "preparing"
    if claimed is not None:
        assert claimed[1].id == UUID(original["items"][1]["id"])


async def test_live_link_guards_edit_and_wrong_project_target(client, setup_work, session):
    project, _, _, original, replacement, root, read, _ = await fixture(client, setup_work, session)
    endpoint = f"/api/v1/projects/{project['id']}/work-plans/{replacement['id']}"
    # A separate unstarted endpoint remains editable only after explicit withdrawal.
    second = await create(client, project, spec(state="draft"))
    lid = read["links"][0]["id"]
    _withdrawn = (
        await client.post(root + "/" + lid + "/withdraw", json=command(read, read["links"][0]["current_replacement"]))
    ).json()
    r = (await client.get(root, params={"replacement_item_id": second["items"][0]["id"]})).json()
    linked = await client.post(
        root, json=command(r, r["candidate"]) | {"replacement_item_id": second["items"][0]["id"]}
    )
    assert linked.status_code == 200
    endpoint = f"/api/v1/projects/{project['id']}/work-plans/{second['id']}"
    edit = spec(state="draft", expected_revision=second["revision"])
    edit.pop("state")
    edit["items"][0]["description"] = "changed"
    response = await client.put(endpoint, json=edit)
    assert response.status_code == 409, response.text
    assert (await client.get(root, params={"replacement_item_id": str(uuid4())})).status_code == 404
    body = accept_command(linked.json(), original["items"][1])
    # Candidate is unmerged, and cannot be accepted regardless of caller-supplied merge fields.
    body.update(merge_sha="a" * 40, execution_id=str(uuid4()))
    assert (
        await client.post(root + "/" + linked.json()["result"]["link_id"] + "/acceptances", json=body)
    ).status_code == 409
