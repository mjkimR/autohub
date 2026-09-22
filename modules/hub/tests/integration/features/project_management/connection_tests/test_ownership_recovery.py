import json
from copy import deepcopy
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.project_management.connection_tests.catalogs import prepare_dispatch
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app_testing_base import utc_now
from sqlalchemy import update
from tests.integration.features.project_management.connection_tests.test_connection_tests import (
    github as github,
)
from tests.integration.features.project_management.connection_tests.test_connection_tests import (
    jules as jules,
)
from tests.integration.features.project_management.connection_tests.test_connection_tests import (
    project as project,
)
from tests.integration.features.project_management.connection_tests.test_connection_tests import (
    start_jules,
    step,
)

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def test_default_branch_inheriting_test_commit_never_grants_cleanup_ownership(
    client,
    project,
    github,
    jules,
    session,
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    # External merge commit M incorporates test commit A, then ordinary work D starts from M.
    # A -> test output C -> main M -> unrelated work D. Both PR heads are ahead of A.
    github.pr.update(state="closed", merged=True)
    github.pr["base"] = {"ref": "main", "sha": "e" * 40}
    ordinary = deepcopy(github.pr)
    ordinary.update(
        number=43,
        state="open",
        merged=False,
        title="Regular feature",
        body="",
        labels=[],
        html_url="https://github.com/owner/app/pull/43",
    )
    ordinary["head"].update(ref="feature/regular-work", sha="d" * 40)
    original = github.respond
    deleted = []

    def respond(request):
        path = request.url.path
        if request.method == "DELETE" and "/git/refs/heads/" in path:
            deleted.append(path)
            return httpx.Response(204)
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "e" * 40}})
        if "/compare/" in path:
            assert path.split("/compare/")[1].split("...")[0] == test["evidence"]["initial_sha"]
            return httpx.Response(200, json={"status": "ahead"})
        if path.endswith("/pulls") and request.method == "GET":
            return httpx.Response(200, json=[ordinary, github.pr])
        if path.endswith("/pulls/43"):
            if request.method == "PATCH":
                ordinary["state"] = json.loads(request.content)["state"]
            return httpx.Response(200, json=deepcopy(ordinary))
        return original(request)

    github.respond = respond
    test = await step(client, test, "cancel")
    assert ordinary["state"] == "open"
    assert "43" in test["evidence"]["unconfirmed_pulls"]
    assert "43" not in test["evidence"]["owned_pulls"]
    assert ordinary["body"] == "" and ordinary["labels"] == []
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            finished_at=utc_now() - timedelta(days=2),
        )
    )
    await session.commit()
    test = await step(client, test)
    assert test["cleanup_status"] == "waiting"
    assert ordinary["state"] == "open"
    assert not deleted
    assert await ConnectionTestRepository().owns_pull(session, "owner/app", 43)
    response = await client.post(
        f"/api/v1/projects/{project['id']}/connection-tests/{test['id']}/resolve-cleanup",
        json={
            "request_id": str(uuid4()),
            "confirmed_remote_stopped": True,
            "note": "The test was externally merged; PR 43 is ordinary work from main.",
            "unrelated_pulls": {"43": "d" * 40},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["cleanup_status"] == "completed"
    assert not await ConnectionTestRepository().owns_pull(session, "owner/app", 43)
    assert ordinary["state"] == "open"
    assert not any(path.endswith("feature/regular-work") for path in deleted)


async def test_intent_without_post_can_be_resolved_without_creating_a_session(
    client,
    project,
    github,
    jules,
    session,
):
    test = await step(client, await start_jules(client, project, jules))
    row = await session.get(ConnectionTest, UUID(test["id"]))
    assert await prepare_dispatch(session, row) == (True, True)
    await session.commit()
    # The worker dies here before POST /sessions, with its create intent already durable.
    test = await step(client, test)
    assert not jules.creates and jules.remote is None
    test = await step(client, test, "cancel")
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            finished_at=utc_now() - timedelta(days=30),
        )
    )
    await session.commit()
    for _ in range(3):
        test = await step(client, test)
        assert test["cleanup_status"] == "waiting"
        assert test["evidence"]["output_discovery_pending"]
    assert await ConnectionTestRepository().protected_heads(session, "owner/app")
    assert not jules.creates
    path = f"/api/v1/projects/{project['id']}/connection-tests/{test['id']}/resolve-cleanup"
    body = {
        "request_id": str(uuid4()),
        "confirmed_remote_stopped": True,
        "note": "Checked provider history; no session was ever created.",
        "unrelated_pulls": {},
    }
    assert (await client.post(path, json={**body, "confirmed_remote_stopped": False})).status_code == 422
    assert (await client.post(path, json={**body, "note": "  "})).status_code == 422
    result = await client.post(path, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["cleanup_status"] == "completed"
    assert result.json()["status"] == "canceled"
    assert not await ConnectionTestRepository().protected_heads(session, "owner/app")
    assert not jules.creates and jules.remote is None
    assert (await client.post(path, json=body)).status_code == 200
    assert (await client.post(path, json={**body, "note": "Different decision"})).status_code == 409


async def test_cleanup_resolution_rejects_active_leases_and_stale_candidate_heads(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    path = f"/api/v1/projects/{project['id']}/connection-tests/{test['id']}/resolve-cleanup"
    body = {"request_id": str(uuid4()), "confirmed_remote_stopped": True, "note": "Checked", "unrelated_pulls": {}}
    assert (await client.post(path, json=body)).status_code == 409
    test = await step(client, test, "cancel")
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            lease_token=uuid4(),
            lease_until=utc_now() + timedelta(seconds=90),
        )
    )
    await session.commit()
    assert (await client.post(path, json=body)).status_code == 409
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            lease_token=None,
            lease_until=None,
            evidence={
                **test["evidence"],
                "unconfirmed_pulls": {
                    "43": {"sha": "d" * 40, "branch": "feature", "url": "https://github.com/owner/app/pull/43"}
                },
            },
        )
    )
    await session.commit()
    assert (await client.post(path, json=body)).status_code == 409
    assert (await client.post(path, json={**body, "unrelated_pulls": {"43": "e" * 40}})).status_code == 409
    wrong_project = path.replace(project["id"], str(uuid4()))
    assert (await client.post(wrong_project, json=body)).status_code == 404


async def test_provider_owned_pr_gets_marker_and_label_even_when_agent_omits_them(client, project, github, jules):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    github.pr["body"] = "Agent omitted the requested marker"
    test = await step(client, test)
    assert f"<!-- autohub-connection-test:{test['id']} -->" in github.pr["body"]
    assert {"name": "autohub-connection-test"} in github.pr["labels"]
    assert test["evidence"]["owned_pulls"]["42"]["proof"] == "provider_output"


async def test_label_permission_failure_does_not_prevent_owned_pr_cleanup(client, project, github, jules):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    original = github.respond

    def respond(request):
        if "/labels" in request.url.path:
            return httpx.Response(403)
        return original(request)

    github.respond = respond
    test = await step(client, test)
    assert test["status"] == "succeeded"
    assert test["evidence"]["marking_warnings"]
    test = await step(client, test)
    assert github.pr["state"] == "closed" and test["cleanup_status"] == "completed"


@pytest.mark.parametrize("legacy_owned_record", [True, False])
async def test_legacy_ancestry_record_requires_new_ownership_proof(
    client, project, github, jules, session, legacy_owned_record
):
    from app.features.configuration.connectors.models import Connector
    from tests.integration.features.project_management.connection_tests.test_cleanup_safety import disable_jules

    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.complete(test["id"])
    github.pr.update(body="", title="Unmarked output")
    legacy = {
        **test["evidence"],
        "execution_finished": True,
        "provider_output_confirmed": True,
        "output_discovery_pending": False,
        "pull_number": 42,
        "owned_pulls": {"42": {"branch": github.pr["head"]["ref"], "url": github.pr["html_url"]}},
    }
    if not legacy_owned_record:
        legacy.pop("owned_pulls")
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(
            status="canceled",
            finished_at=utc_now() - timedelta(days=2),
            evidence=legacy,
        )
    )
    await session.commit()
    connector_id = await disable_jules(session, jules)
    test = await step(client, test)
    assert github.pr["state"] == "open" and github.pr["body"] == ""
    assert test["evidence"]["unconfirmed_pulls"]["42"]
    assert test["cleanup_status"] == "waiting"
    assert not test["evidence"]["pr_closed"]
    await session.execute(update(Connector).where(Connector.id == connector_id).values(enabled=True))
    await session.commit()
    test = await step(client, test)
    assert test["evidence"]["owned_pulls"]["42"]["proof"] == "provider_output"
    assert github.pr["state"] == "closed" and test["cleanup_status"] == "completed"


@pytest.mark.parametrize(
    "metadata",
    [
        {"labels": [{"name": "autohub-connection-test"}]},
        {"body": "<!-- autohub-connection-test:example -->"},
    ],
)
async def test_visible_test_metadata_blocks_enrollment_without_known_id(client, project, github, metadata):
    github.pr = {
        "number": 42,
        "head": {"ref": "ordinary-head"},
        "base": {"ref": "main"},
        **metadata,
    }
    response = await client.post(
        f"/api/v1/projects/{project['id']}/runs", json={"pull_number": 42, "implemented": True}
    )
    assert response.status_code == 422, response.text
    assert "Connection test" in response.text
