import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.auth import MCP_READ, MCP_WRITE
from app.features.project_management.pipeline_runs.models import ExecutionAttempt
from app.features.project_management.pipelines import services
from app.mcp import auth, dependencies
from app_prebuilt_auth.api_key.models import Machine, MachineKey
from app_testing_base import utc_now

pytestmark = [pytest.mark.integration, pytest.mark.real_commit]
ROOT = {"X-Root-API-Key": "root-test-credential-at-least-32-characters"}
HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"}


@pytest.fixture(autouse=True)
async def transport(app, session_maker, session, monkeypatch, credential_key_provider):
    async def maker():
        return session_maker

    monkeypatch.setattr(auth, "get_api_key_session_maker", maker)
    monkeypatch.setattr(dependencies, "get_credential_key_provider", lambda: credential_key_provider)
    started, stopped = asyncio.Event(), asyncio.Event()

    async def lifespan():
        try:
            async with app.router.lifespan_context(app):
                started.set()
                await stopped.wait()
        finally:
            started.set()

    task = asyncio.create_task(lifespan())
    await started.wait()
    if task.done():
        task.result()
    try:
        yield
    finally:
        stopped.set()
        await task


async def issue(client, scopes):
    machine = await client.post("/api/v1/machines", headers=ROOT, json={"name": str(uuid4()), "scopes": scopes})
    assert machine.status_code == 201, machine.text
    key = await client.post(f"/api/v1/machines/{machine.json()['id']}/keys", headers=ROOT, json={"label": "mcp-test"})
    assert key.status_code == 201, key.text
    return machine.json(), key.json()


@pytest.fixture
async def key(client):
    _, result = await issue(client, [MCP_READ, MCP_WRITE])
    return result["key"]


async def rpc(client, key, method, params=None):
    return await client.post(
        "/mcp/",
        headers=HEADERS | {"Authorization": f"Bearer {key}"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


async def call(client, key, name, arguments=None, *, error=False):
    response = await rpc(client, key, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result.get("isError", False) == error, result
    return result["structuredContent"]


async def test_handshake_auth_discovery_and_scope_isolation(client, key):
    assert (await client.post("/mcp/", json={})).status_code == 401
    assert (await client.get("/mcp/", headers=ROOT)).status_code == 401
    assert (await rpc(client, "invalid", "tools/list")).status_code == 401
    _, scheduler = await issue(client, ["autohub:dispatch"])
    assert (await rpc(client, scheduler["key"], "tools/list")).status_code == 403
    init = await rpc(
        client,
        key,
        "initialize",
        {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
    )
    assert init.status_code == 200, init.text
    tools = (await rpc(client, key, "tools/list")).json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert {"projects.list", "runs.enroll", "runs.get", "connection_tests.start", "connection_tests.list"} <= names
    assert not any(word in name for name in names for word in ("lease", "complete", "dispatch", "delete", "key"))
    schema = next(tool["inputSchema"] for tool in tools if tool["name"] == "runs.list")
    assert schema["properties"]["limit"]["maximum"] == 100
    _, reader = await issue(client, [MCP_READ])
    denied = await call(client, reader["key"], "projects.create", {"project": {"name": "Denied"}}, error=True)
    assert denied["error"]["code"] == "MCP_FORBIDDEN"
    created = await call(client, key, "projects.create", {"project": {"name": "Allowed"}})
    assert created["result"]["name"] == "Allowed"
    assert (await call(client, reader["key"], "projects.list"))["result"]["total_count"] == 1
    invalid = await call(client, key, "projects.list", {"limit": 101}, error=True)
    assert invalid["error"]["code"] == "MCP_INVALID_ARGUMENTS"
    missing = await call(client, key, "projects.get", {"project_id": str(uuid4())}, error=True)
    assert missing["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("change", ["revoked", "expired", "inactive"])
async def test_key_changes_take_effect_on_next_request(client, session_maker, change):
    machine, key = await issue(client, [MCP_READ])
    assert (await rpc(client, key["key"], "tools/list")).status_code == 200
    async with session_maker() as session:
        if change == "inactive":
            row = await session.get(Machine, UUID(machine["id"]))
            row.is_active = False
        else:
            row = await session.get(MachineKey, UUID(key["id"]))
            setattr(row, "revoked_at" if change == "revoked" else "expires_at", utc_now() - timedelta(seconds=1))
        await session.commit()
    assert (await rpc(client, key["key"], "tools/list")).status_code == 401


async def test_origin_and_spa_route_are_protected(client, key):
    response = await client.post(
        "/mcp",
        headers=HEADERS | {"Authorization": f"Bearer {key}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    )
    assert response.status_code == 200, response.text
    assert "tools" in response.json()["result"]
    response = await client.post(
        "/mcp/", headers=HEADERS | {"Authorization": f"Bearer {key}", "Origin": "https://untrusted.example"}, json={}
    )
    assert response.status_code == 403


async def test_project_enrollment_and_outcomes_reuse_business_rules(client, key, monkeypatch, session_maker):
    def github(request):
        assert request.method == "GET"
        if request.url.path == "/repos/owner/app":
            return httpx.Response(200, json={"default_branch": "main"})
        if request.url.path == "/repos/owner/app/pulls":
            return httpx.Response(200, json=[])
        assert request.url.path == "/repos/owner/app/pulls/7"
        return httpx.Response(
            200,
            json={
                "number": 7,
                "state": "open",
                "title": "Implement health",
                "body": "private PR body",
                "html_url": "https://github.com/owner/app/pull/7",
                "head": {"ref": "feature", "sha": "a" * 40, "repo": {"full_name": "owner/app"}},
                "base": {"ref": "main", "sha": "b" * 40, "repo": {"full_name": "owner/app"}},
            },
        )

    monkeypatch.setattr(
        services,
        "create_github_client",
        lambda token: httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(github)),
    )
    connector = await client.post(
        "/api/v1/connectors",
        json={"name": "GitHub", "provider": "github", "credentials": {"token": "secret-not-for-mcp"}},
    )
    assert connector.status_code == 201, connector.text
    connectors = await call(client, key, "connectors.list")
    assert connectors["result"]["items"][0]["id"] == connector.json()["id"]
    assert "secret-not-for-mcp" not in str(connectors)
    config = {
        "name": "App",
        "github": {
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["lint"], "event": "pull_request"},
        },
    }
    project = (await call(client, key, "projects.create", {"project": config}))["result"]
    project_id = project["id"]
    assert project["github_connector_name"] == "GitHub"
    found = await call(client, key, "projects.list", {"search": "owner/app"})
    assert found["result"]["items"][0]["id"] == project_id
    by_repository = await call(client, key, "projects.get", {"repository": "Owner/App"})
    assert by_repository["result"]["id"] == project_id
    unknown = await call(client, key, "projects.get", {"repository": "owner/unknown"}, error=True)
    assert unknown["error"]["code"] == "NOT_FOUND"
    ambiguous = await call(
        client, key, "projects.get", {"project_id": project_id, "repository": "owner/app"}, error=True
    )
    assert ambiguous["error"]["code"] == "MCP_INVALID_ARGUMENTS"
    update = {
        "project_id": project_id,
        "project": {"expected_revision": project["revision"], "github": {"automation": {"auto_merge": False}}},
    }
    updated = (await call(client, key, "projects.update", update))["result"]
    assert updated["github"]["automation"]["auto_merge"] is False
    assert updated["github"]["verification"] == config["github"]["verification"]
    renamed = {"project_id": project_id, "project": {"expected_revision": updated["revision"], "name": "Renamed"}}
    renamed_result = (await call(client, key, "projects.update", renamed))["result"]
    assert renamed_result["name"] == "Renamed"
    assert renamed_result["github"]["automation"]["auto_merge"] is False
    stale = await call(client, key, "projects.update", update, error=True)
    assert stale["error"]["code"] == "CONFLICT"
    invalid_patch = {"expected_revision": renamed_result["revision"], "github": {"automation": {"auto_merge": None}}}
    invalid = await call(
        client, key, "projects.update", {"project_id": project_id, "project": invalid_patch}, error=True
    )
    assert invalid["error"]["code"] == "INVALID_REQUEST"
    assert "auto_merge" in invalid["error"]["message"]
    args = {"project_id": project_id, "pull_request": {"pull_number": 7, "implemented": True}}
    run = (await call(client, key, "runs.enroll", args))["result"]
    assert run["state"] == "awaiting_ci"
    assert run["catalog_key"]
    assert "private PR body" not in str(run)
    duplicate = await call(client, key, "runs.enroll", args, error=True)
    assert duplicate["error"]["code"] == "CONFLICT"
    assert (await call(client, key, "runs.list", {"project_id": project_id}))["result"]["total_count"] == 1
    assert (await call(client, key, "runs.list", {"pull_number": 7}))["result"]["items"][0]["id"] == run["id"]
    assert (await call(client, key, "runs.list", {"pull_number": 70}))["result"]["total_count"] == 0
    run_args = {"run_id": run["id"]}
    outcomes = (await call(client, key, "runs.attempts", run_args))["result"]
    assert len(outcomes["items"]) == 1
    assert "request_snapshot" not in str(outcomes)
    assert (await call(client, key, "runs.pause", run_args))["result"]["state"] == "paused"
    assert (await call(client, key, "runs.resume", run_args))["result"]["state"] == "awaiting_ci"
    assert (await call(client, key, "runs.cancel", run_args))["result"]["state"] == "canceled"
    # A settled run returns at once even when asked to wait.
    assert (await call(client, key, "runs.get", run_args | {"wait_seconds": 20}))["result"]["state"] == "canceled"
    # A later page must retain totals and summary across the entire history.
    async with session_maker() as session:
        session.add(
            ExecutionAttempt(
                pipeline_run_id=UUID(run["id"]),
                attempt_number=2,
                kind="ci-fix",
                state="failed",
                request_snapshot={},
                request_digest="second-attempt",
                idempotency_key=uuid4(),
            )
        )
        await session.commit()
    page = (await call(client, key, "runs.attempts", run_args | {"offset": 1, "limit": 1}))["result"]
    assert [item["attempt_number"] for item in page["items"]] == [2]
    assert page["total_count"] == 2
    assert page["summary"]["attempts_by_kind"] == {"implementation": 1, "ci-fix": 1}
    empty = (await call(client, key, "runs.attempts", run_args | {"offset": 2, "limit": 1}))["result"]
    assert empty["items"] == [] and empty["total_count"] == 2
    catalogs = (await call(client, key, "catalogs.list"))["result"]["items"]
    assert catalogs
    options = (await call(client, key, "projects.readiness", {"project_id": project_id}))["result"]["items"]
    assert options and all("spec" not in option for option in options)
    assert all(item["status"] != "configured" for option in options for item in option["pending"])
    request = {"project_id": project_id, "request_id": str(uuid4())}
    first = (await call(client, key, "connection_tests.start", request))["result"]
    repeated = (await call(client, key, "connection_tests.start", request))["result"]
    assert first["id"] == repeated["id"]
    listed = (await call(client, key, "connection_tests.list", {"project_id": project_id}))["result"]
    assert [test["id"] for test in listed["items"]] == [first["id"]]
    current = await call(client, key, "connection_tests.get", {"project_id": project_id, "test_id": first["id"]})
    assert current["result"]["cleanup_status"] == "pending"
    assert isinstance(current["result"]["evidence"], dict)
    assert current["result"]["phase_label"]

    canceled = await call(client, key, "connection_tests.cancel", {"project_id": project_id, "test_id": first["id"]})
    assert canceled["result"]["cancel_requested"] is True
    assert canceled["result"]["status"] == "canceled"
    assert canceled["result"]["cleanup_status"] == "waiting"
