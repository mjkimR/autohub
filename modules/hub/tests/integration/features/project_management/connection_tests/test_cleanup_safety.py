from copy import deepcopy
from datetime import timedelta
from uuid import UUID

import httpx
import pytest
from app.features.ai_catalogs.models import AICatalog
from app.features.configuration.connectors.models import Connector
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
    start,
    start_jules,
    step,
)

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]


async def expire_grace(session, test):
    await session.execute(
        update(ConnectionTest)
        .where(ConnectionTest.id == UUID(test["id"]))
        .values(finished_at=utc_now() - timedelta(days=2))
    )
    await session.commit()


async def disable_jules(session, jules):
    catalog = await session.get(AICatalog, UUID(jules.catalog_id))
    await session.execute(update(Connector).where(Connector.id == catalog.connector_id).values(enabled=False))
    await session.commit()
    return catalog.connector_id


async def test_unmarked_wrong_base_output_is_quarantined_until_provider_confirms_it(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    connector_id = await disable_jules(session, jules)
    test = await step(client, test, "cancel")
    await expire_grace(session, test)
    # Output arrives after the old protection cutoff, without either requested ref or marker.
    jules.complete(test["id"])
    github.pr.update(title="Verify connection", body="", draft=False)
    github.pr["base"]["ref"] = "main"
    enroll_path = f"/api/v1/projects/{project['id']}/runs"
    blocked = await client.post(enroll_path, json={"pull_number": 42, "implemented": True})
    assert blocked.status_code == 422, blocked.text
    assert "Connection test" in blocked.text
    test = await step(client, test)
    assert github.pr["state"] == "open"
    assert "42" in test["evidence"]["unconfirmed_pulls"]
    assert test["cleanup_status"] == "waiting"
    assert test["evidence"]["output_discovery_pending"]
    assert not any(method == "DELETE" for method, _, _ in github.writes)
    assert await ConnectionTestRepository().owns_pull(session, "owner/app", 42)

    await session.execute(update(Connector).where(Connector.id == connector_id).values(enabled=True))
    await session.commit()
    test = await step(client, test)
    assert test["status"] == "canceled" and test["cleanup_status"] == "completed"
    assert github.pr["state"] == "closed"
    # Even reopening and retargeting a known PR cannot make it a development run.
    github.pr["state"] = "open"
    assert (await client.post(enroll_path, json={"pull_number": 42, "implemented": True})).status_code == 422


async def test_cleanup_discovery_pages_across_bases_without_touching_unrelated_prs(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    await disable_jules(session, jules)
    jules.complete(test["id"])
    github.pr["base"]["ref"] = "main"
    unrelated = deepcopy(github.pr)
    unrelated.update(number=99, html_url="https://github.com/owner/app/pull/99")
    unrelated["head"].update(ref="ordinary-work", sha="d" * 40)
    older = deepcopy(unrelated)
    older["created_at"] = (utc_now() - timedelta(days=2)).isoformat()
    original = github.respond
    pages = []

    def respond(request):
        if request.method == "GET" and request.url.path.endswith("/pulls"):
            assert "base" not in request.url.params
            assert request.url.params["sort"] == "created"
            pages.append(request.url.params["page"])
            return httpx.Response(200, json=[unrelated] * 100 if pages[-1] == "1" else [github.pr, older])
        if "/compare/" in request.url.path and request.url.path.endswith("d" * 40):
            return httpx.Response(200, json={"status": "diverged"})
        assert not request.url.path.endswith("/pulls/99")
        return original(request)

    github.respond = respond
    test = await step(client, test, "cancel")
    assert pages == ["1", "2"]
    assert github.pr["state"] == "closed"
    assert set(test["evidence"]["owned_pulls"]) == {"42"}
    assert unrelated["state"] == "open"


@pytest.mark.parametrize("provider_available", [False, True])
async def test_incomplete_github_discovery_cannot_retire_protection(
    client, project, github, jules, session, provider_available
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    if not provider_available:
        await disable_jules(session, jules)
    test = await step(client, test, "cancel")
    await expire_grace(session, test)
    jules.complete(test["id"])
    # A terminal response without outputs still needs a complete GitHub scan.
    jules.remote["outputs"] = []
    original = github.respond

    def respond(request):
        if "/compare/" in request.url.path:
            return httpx.Response(503)
        return original(request)

    github.respond = respond
    test = await step(client, test)
    assert test["cleanup_status"] == "failed"
    assert test["evidence"]["output_discovery_pending"]
    assert await ConnectionTestRepository().protected_heads(session, "owner/app")
    assert not any(method == "DELETE" for method, _, _ in github.writes)


@pytest.mark.parametrize("remote_state", ["COMPLETED", "FAILED"])
async def test_confirmed_terminal_session_without_pr_can_finish_cleanup(
    client, project, github, jules, session, remote_state
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    jules.remote.update(state=remote_state, outputs=[])
    test = await step(client, test, "cancel")
    await expire_grace(session, test)
    test = await step(client, test)
    assert test["cleanup_status"] == "completed"
    assert not test["evidence"]["output_discovery_pending"]
    assert not await ConnectionTestRepository().protected_heads(session, "owner/app")


async def test_new_probe_needs_no_dedicated_schedule(client, project, github):
    test = await step(client, await start(client, project))
    assert (await client.get(f"/api/v1/schedule_configs/{test['id']}")).status_code == 404
    test = await step(client, test, "cancel")
    assert test["status"] == "canceled" and github.pr["state"] == "closed"


async def test_generic_schedule_api_cannot_create_duplicate_test_workers(client, project, github):
    test = await start(client, project)
    payload = {
        "name": "Duplicate",
        "task_func": "pipeline.connection_test",
        "interval_seconds": 60,
        "payload": {"test_id": test["id"]},
    }
    response = await client.post("/api/v1/schedule_configs", json=payload)
    assert response.status_code == 409, response.text
    ordinary = await client.post("/api/v1/schedule_configs", json={**payload, "task_func": "hello_world"})
    assert ordinary.status_code == 201, ordinary.text
    response = await client.patch(f"/api/v1/schedule_configs/{ordinary.json()['id']}", json=payload)
    assert response.status_code == 409, response.text


async def test_detached_github_connector_is_retained_until_cleanup_completes(client, project, github, session):
    test = await step(client, await start(client, project))
    detached = await client.put(
        f"/api/v1/projects/{project['id']}",
        json={
            "name": project["name"],
            "github": None,
            "expected_revision": project["revision"],
        },
    )
    assert detached.status_code == 200, detached.text
    path = f"/api/v1/connectors/{project['github']['github_connector_id']}"
    response = await client.delete(path)
    assert response.status_code == 409, response.text
    assert "finish its cleanup" in response.text
    test = await step(client, test)
    assert test["status"] == "canceled" and github.pr["state"] == "closed"
    assert (await client.delete(path)).status_code == 409
    await expire_grace(session, test)
    test = await step(client, test)
    assert test["cleanup_status"] == "completed"
    response = await client.delete(path)
    assert response.status_code == 200, response.text


async def test_replaced_catalog_connector_is_retained_for_provider_reconciliation(
    client, project, github, jules, session
):
    test = await step(client, await step(client, await start_jules(client, project, jules)))
    connector_id = test["catalog_snapshot"]["connector_id"]
    await session.execute(update(AICatalog).where(AICatalog.id == UUID(jules.catalog_id)).values(connector_id=None))
    await session.commit()
    path = f"/api/v1/connectors/{connector_id}"
    assert (await client.delete(path)).status_code == 409
    jules.complete(test["id"])
    test = await step(client, test)
    assert test["status"] == "canceled" and github.pr["state"] == "closed"
    await expire_grace(session, test)
    test = await step(client, test)
    assert test["cleanup_status"] == "completed"
    assert (await client.delete(path)).status_code == 200
