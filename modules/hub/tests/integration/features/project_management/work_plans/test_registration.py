import asyncio
from uuid import UUID, uuid4

import pytest
from tests.integration.features.project_management.work_plans.test_work_plans import due

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


def payload():
    return {
        "request_id": str(uuid4()),
        "title": "Approved work",
        "items": [
            {"key": "base", "title": "Foundation", "description": "Implement base", "acceptance": "Tests pass"},
            {
                "key": "use",
                "title": "Consumer",
                "description": "Consume base",
                "acceptance": "Tests pass",
                "depends_on": ["base"],
            },
        ],
    }


async def test_replay_recovers_original_even_after_plan_changes(client, setup_work):
    project, _, _, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    data = payload()
    first = await client.post(root, json=data)
    assert first.status_code == 201, first.text
    plan = first.json()
    paused = await client.post(
        root + f"/{plan['id']}/control", json={"action": "pause", "expected_revision": plan["revision"]}
    )
    assert paused.status_code == 200
    replay = await client.post(root, json=data)
    assert replay.json()["id"] == plan["id"]
    assert replay.json()["state"] == "paused"
    assert (await client.get(root)).json()["total_count"] == 1
    recovered = await client.get(root + f"/registrations/{data['request_id']}")
    assert recovered.json()["id"] == plan["id"]
    conflict = await client.post(root, json=data | {"title": "Different work"})
    assert conflict.status_code == 409
    reordered = await client.post(root, json=data | {"items": list(reversed(data["items"]))})
    assert reordered.json()["id"] == plan["id"]


async def test_registration_retry_after_pr_response_loss_does_not_duplicate_work(client, setup_work, session):
    project, github, worker, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    data = payload()
    first = (await client.post(root, json=data)).json()
    github.lose_pull_response = True
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1
    assert (await client.post(root, json=data)).json()["id"] == first["id"]
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 1
    recovered = (await client.get(root + f"/registrations/{data['request_id']}")).json()
    assert recovered["items"][0]["pipeline_run_id"]
    assert recovered["items"][1]["state"] == "waiting"


async def test_replacement_keeps_canceled_evidence_and_does_not_release_old_dependents(client, setup_work, session):
    project, github, worker, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    original = (await client.post(root, json=payload())).json()
    await worker.advance_project(UUID(project["id"]))
    original = (await client.get(root + f"/{original['id']}")).json()
    run_id = original["items"][0]["pipeline_run_id"]
    assert (await client.post(f"/api/v1/pipeline-runs/{run_id}/cancel")).status_code == 200
    github.pulls[100]["state"] = "closed"
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    original = (await client.get(root + f"/{original['id']}")).json()
    assert original["items"][0]["state"] != "succeeded"
    assert original["items"][1]["state"] == "waiting"
    revoked = await client.post(
        root + f"/{original['id']}/control", json={"action": "revoke", "expected_revision": original["revision"]}
    )
    assert revoked.status_code == 200, revoked.text
    replacement = (
        await client.post(
            root,
            json=payload()
            | {
                "description": f"Replaces plan {original['id']}; canceled run /projects/runs?run={run_id}; original PR https://github.com/owner/app/pull/100"
            },
        )
    ).json()
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 2
    github.merge(101)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    assert len(github.pulls) == 3
    github.merge(102)
    await due(session)
    await worker.advance_project(UUID(project["id"]))
    completed = (await client.get(root + f"/{replacement['id']}")).json()
    assert completed["state"] == "completed"
    retained = (await client.get(root + f"/{original['id']}")).json()
    assert retained["state"] == "revoked"
    assert retained["items"][0]["state"] != "succeeded"
    assert retained["items"][1]["state"] == "revoked"
    assert (await client.get(f"/api/v1/pipeline-runs/{run_id}")).json()["state"] == "canceled"
    assert original["id"] in completed["description"]


async def test_concurrent_registration_creates_one_plan(client, setup_work, is_postgres):
    if not is_postgres:
        pytest.skip("Row lock concurrency requires PostgreSQL")
    project, _, _, _ = setup_work
    root = f"/api/v1/projects/{project['id']}/work-plans"
    data = payload()
    responses = await asyncio.gather(*(client.post(root, json=data) for _ in range(3)))
    assert all(r.status_code == 201 for r in responses), [r.text for r in responses]
    assert len({r.json()["id"] for r in responses}) == 1
    assert (await client.get(root)).json()["total_count"] == 1
