import asyncio
import re
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.auth import MCP_OPS, MCP_READ, MCP_WRITE
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


@pytest.fixture
async def ops_key(client):
    _, result = await issue(client, [MCP_OPS])
    return result["key"]


async def rpc(client, key, method, params=None, *, path="/mcp/"):
    return await client.post(
        path,
        headers=HEADERS | {"Authorization": f"Bearer {key}"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


async def call(client, key, name, arguments=None, *, error=False, path="/mcp/"):
    response = await rpc(client, key, "tools/call", {"name": name, "arguments": arguments or {}}, path=path)
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result.get("isError", False) == error, result
    return result["structuredContent"]


async def ops_call(client, key, name, arguments=None, *, error=False):
    return await call(client, key, name, arguments, error=error, path="/ops/mcp/")


async def test_handshake_auth_discovery_and_scope_isolation(client, key, ops_key):
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
    assert {"projects_list", "runs_enroll", "runs_get", "connection_tests_list"} <= names
    assert not any(word in name for name in names for word in ("lease", "complete", "dispatch", "delete", "key"))
    schema = next(tool["inputSchema"] for tool in tools if tool["name"] == "runs_list")
    assert schema["properties"]["limit"]["maximum"] == 100
    _, reader = await issue(client, [MCP_READ])
    denied = await call(client, reader["key"], "runs_cancel", {"run_id": str(uuid4())}, error=True)
    assert denied["error"]["code"] == "MCP_FORBIDDEN"
    created = await ops_call(client, ops_key, "projects_create", {"project": {"name": "Allowed"}})
    assert created["result"]["name"] == "Allowed"
    assert (await call(client, reader["key"], "projects_list"))["result"]["total_count"] == 1
    invalid = await call(client, key, "projects_list", {"limit": 101}, error=True)
    assert invalid["error"]["code"] == "MCP_INVALID_ARGUMENTS"
    missing = await call(client, key, "projects_get", {"project_id": str(uuid4())}, error=True)
    assert missing["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("scopes,path", [([MCP_READ], "/mcp/"), ([MCP_OPS], "/ops/mcp/")])
@pytest.mark.parametrize("change", ["revoked", "expired", "inactive"])
async def test_key_changes_take_effect_on_next_request(client, session_maker, change, scopes, path):
    machine, key = await issue(client, scopes)
    assert (await rpc(client, key["key"], "tools/list", path=path)).status_code == 200
    async with session_maker() as session:
        if change == "inactive":
            row = await session.get(Machine, UUID(machine["id"]))
            row.is_active = False
        else:
            row = await session.get(MachineKey, UUID(key["id"]))
            setattr(row, "revoked_at" if change == "revoked" else "expires_at", utc_now() - timedelta(seconds=1))
        await session.commit()
    assert (await rpc(client, key["key"], "tools/list", path=path)).status_code == 401


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


async def test_project_enrollment_and_outcomes_reuse_business_rules(client, key, ops_key, monkeypatch, session_maker):
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
    connectors = await call(client, key, "projects_options", {"connectors_page": {}})
    assert connectors["result"]["connectors"]["items"][0]["id"] == connector.json()["id"]
    assert "secret-not-for-mcp" not in str(connectors)
    config = {
        "name": "App",
        "github": {
            "repository": "owner/app",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["lint"], "event": "pull_request"},
            "automation": {"auto_merge": True},
        },
    }
    project = (await ops_call(client, ops_key, "projects_create", {"project": config}))["result"]
    project_id = project["id"]
    assert project["github_connector_name"] == "GitHub"
    found = await call(client, key, "projects_list", {"search": "owner/app"})
    assert found["result"]["items"][0]["id"] == project_id
    by_repository = await call(client, key, "projects_get", {"repository": "Owner/App"})
    assert by_repository["result"]["id"] == project_id
    unknown = await call(client, key, "projects_get", {"repository": "owner/unknown"}, error=True)
    assert unknown["error"]["code"] == "NOT_FOUND"
    ambiguous = await call(
        client, key, "projects_get", {"project_id": project_id, "repository": "owner/app"}, error=True
    )
    assert ambiguous["error"]["code"] == "MCP_INVALID_ARGUMENTS"
    update = {
        "project_id": project_id,
        "project": {"expected_revision": project["revision"], "github": {"automation": {"auto_merge": False}}},
    }
    preview = (await ops_call(client, ops_key, "projects_update", update | {"dry_run": True}))["result"]
    assert preview["applied"] is False
    assert preview["revision"] == project["revision"]
    assert preview["changes"] == [{"path": "github.automation.auto_merge", "before": True, "after": False}]
    unchanged = (await call(client, key, "projects_get", {"project_id": project_id}))["result"]
    assert unchanged["github"]["automation"]["auto_merge"] is True
    assert unchanged["revision"] == project["revision"]
    updated = (await ops_call(client, ops_key, "projects_update", update))["result"]
    assert updated["applied"] is True
    assert updated["changes"] == preview["changes"]
    assert updated["github"]["automation"]["auto_merge"] is False
    assert updated["github"]["verification"] == config["github"]["verification"]
    renamed = {"project_id": project_id, "project": {"expected_revision": updated["revision"], "name": "Renamed"}}
    renamed_result = (await ops_call(client, ops_key, "projects_update", renamed))["result"]
    assert renamed_result["name"] == "Renamed"
    assert renamed_result["github"]["automation"]["auto_merge"] is False
    stale = await ops_call(client, ops_key, "projects_update", update, error=True)
    assert stale["error"]["code"] == "CONFLICT"
    invalid_patch = {"expected_revision": renamed_result["revision"], "github": {"automation": {"auto_merge": None}}}
    invalid = await ops_call(
        client, ops_key, "projects_update", {"project_id": project_id, "project": invalid_patch}, error=True
    )
    assert invalid["error"]["code"] == "INVALID_REQUEST"
    assert "auto_merge" in invalid["error"]["message"]
    args = {"project_id": project_id, "pull_request": {"pull_number": 7, "implemented": True}}
    run = (await call(client, key, "runs_enroll", args))["result"]
    assert run["state"] == "awaiting_ci"
    assert run["catalog_key"]
    assert "private PR body" not in str(run)
    duplicate = await call(client, key, "runs_enroll", args, error=True)
    assert duplicate["error"]["code"] == "CONFLICT"
    assert (await call(client, key, "runs_list", {"project_id": project_id}))["result"]["total_count"] == 1
    assert (await call(client, key, "runs_list", {"pull_number": 7}))["result"]["items"][0]["id"] == run["id"]
    assert (await call(client, key, "runs_list", {"pull_number": 70}))["result"]["total_count"] == 0
    run_args = {"run_id": run["id"]}
    outcomes = (await call(client, key, "runs_attempts", run_args))["result"]
    assert len(outcomes["items"]) == 1
    assert "request_snapshot" not in str(outcomes)
    paused = (await call(client, key, "runs_pause", run_args))["result"]
    assert paused["state"] == "paused"
    stale_resume = await call(
        client,
        key,
        "runs_resume",
        run_args | {"request_id": str(uuid4()), "expected_revision": run["revision"]},
        error=True,
    )
    assert stale_resume["error"]["code"] == "CONFLICT"
    assert (await call(client, key, "runs_get", run_args))["result"]["revision"] == paused["revision"]
    assert (
        await call(
            client, key, "runs_resume", run_args | {"request_id": str(uuid4()), "expected_revision": paused["revision"]}
        )
    )["result"]["state"] == "awaiting_ci"
    assert (await call(client, key, "runs_cancel", run_args))["result"]["state"] == "canceled"
    # A settled run returns at once even when asked to wait.
    assert (await call(client, key, "runs_get", run_args | {"wait_seconds": 20}))["result"]["state"] == "canceled"
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
    page = (await call(client, key, "runs_attempts", run_args | {"offset": 1, "limit": 1}))["result"]
    assert [item["attempt_number"] for item in page["items"]] == [2]
    assert page["total_count"] == 2
    assert page["summary"]["attempts_by_kind"] == {"implementation": 1, "ci-fix": 1}
    empty = (await call(client, key, "runs_attempts", run_args | {"offset": 2, "limit": 1}))["result"]
    assert empty["items"] == [] and empty["total_count"] == 2
    catalogs = (await call(client, key, "projects_options"))["result"]["catalogs"]["items"]
    assert catalogs
    selected = (
        await call(
            client,
            key,
            "projects_options",
            {"project_id": project_id, "capability": "pipeline_delivery", "enabled_only": True, "offset": 100},
        )
    )["result"]
    assert selected["catalogs"]["items"] == []
    assert selected["catalogs"]["total_count"] >= 1
    assert selected["selected_catalog_key"] == "personal-codex"
    assert selected["selection_source"] == "default"
    assert selected["connectors"] is None
    options = (await call(client, key, "projects_readiness", {"project_id": project_id}))["result"]["items"]
    assert options and all("spec" not in option for option in options)
    assert all(item["status"] != "configured" for option in options for item in option["pending"])
    readiness = (
        await call(client, key, "projects_readiness", {"project_id": project_id, "ai_catalog_id": catalogs[0]["id"]})
    )["result"]
    assert readiness["check_kind"] == "configuration_only"
    assert len(readiness["items"]) == 1
    assert readiness["items"][0]["status"] == "manual_checks"
    request = {
        "project_id": project_id,
        "request_id": str(uuid4()),
        "expected_project_revision": renamed_result["revision"],
    }
    stale_test = await ops_call(
        client,
        ops_key,
        "connection_tests_start",
        request | {"expected_project_revision": project["revision"]},
        error=True,
    )
    assert stale_test["error"]["code"] == "CONFLICT"
    first = (await ops_call(client, ops_key, "connection_tests_start", request))["result"]
    repeated = (await ops_call(client, ops_key, "connection_tests_start", request))["result"]
    assert first["id"] == repeated["id"] == request["request_id"]
    assert first["next_action"] == "wait"
    replay_after_change = await ops_call(
        client, ops_key, "connection_tests_start", request | {"expected_project_revision": project["revision"]}
    )
    assert replay_after_change["result"]["id"] == first["id"]
    listed = (await call(client, key, "connection_tests_list", {"project_id": project_id}))["result"]
    assert [test["id"] for test in listed["items"]] == [first["id"]]
    assert listed["history_limit"] == 30 and listed["next_offset"] is None
    assert (await call(client, key, "connection_tests_list", {"project_id": project_id, "status": "succeeded"}))[
        "result"
    ]["items"] == []
    assert (
        await call(
            client,
            key,
            "connection_tests_list",
            {"project_id": project_id, "configuration_current": True, "ai_catalog_id": first["ai_catalog_id"]},
        )
    )["result"]["total_count"] == 1
    current = await call(client, key, "connection_tests_get", {"project_id": project_id, "test_id": first["id"]})
    assert current["result"]["cleanup_status"] == "pending"
    assert isinstance(current["result"]["evidence"], dict)
    assert current["result"]["phase_label"]

    canceled = await ops_call(
        client, ops_key, "connection_tests_cancel", {"project_id": project_id, "test_id": first["id"]}
    )
    assert canceled["result"]["cancel_requested"] is True
    assert canceled["result"]["status"] == "canceled"
    assert canceled["result"]["cleanup_status"] == "waiting"


async def test_surfaces_expose_exact_tools_and_reject_cross_surface_calls(client, key, ops_key):
    reads = {
        "projects_list",
        "projects_get",
        "projects_readiness",
        "projects_options",
        "runs_list",
        "runs_get",
        "runs_attempts",
        "runs_questions",
        "work_plans_list",
        "work_plans_get",
        "connection_tests_list",
        "connection_tests_get",
    }
    work_writes = {
        "runs_enroll",
        "runs_pause",
        "runs_resume",
        "runs_cancel",
        "runs_ask",
        "runs_answer",
        "runs_dismiss_question",
        "work_plans_register",
        "work_plans_update",
        "work_plans_control",
    }
    ops_writes = {"projects_create", "projects_update", "connection_tests_start", "connection_tests_cancel"}
    _, combined = await issue(client, [MCP_READ, MCP_WRITE, MCP_OPS])
    discovered = set()
    for path, credential, expected, excluded in (
        ("/mcp/", key, reads | work_writes, ops_writes),
        ("/ops/mcp/", ops_key, ops_writes, reads | work_writes),
    ):
        tools = (await rpc(client, credential, "tools/list", path=path)).json()["result"]["tools"]
        names = {tool["name"] for tool in tools}
        assert names == expected
        assert all(len(name) <= 64 and re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", name) for name in names)
        assert discovered.isdisjoint(names)
        discovered.update(names)
        for name in excluded:
            # Even a key with every scope cannot reach an unregistered tool.
            result = (
                await rpc(
                    client,
                    combined["key"],
                    "tools/call",
                    {
                        "name": name,
                        "arguments": {},
                    },
                    path=path,
                )
            ).json()["result"]
            assert result["isError"] is True
    # Dotted names are not exposed as compatibility aliases on either surface.
    for path, credential, names in (
        ("/mcp/", key, reads | work_writes),
        ("/ops/mcp/", ops_key, ops_writes),
    ):
        for name in names:
            prefix, operation = name.rsplit("_", 1)
            result = (
                await rpc(
                    client,
                    credential,
                    "tools/call",
                    {
                        "name": f"{prefix}.{operation}",
                        "arguments": {},
                    },
                    path=path,
                )
            ).json()["result"]
            assert result["isError"] is True
    assert len(discovered) == 26
    for removed in ("catalogs.list", "connectors.list"):
        assert removed not in discovered
        result = (await rpc(client, key, "tools/call", {"name": removed, "arguments": {}})).json()["result"]
        assert result["isError"] is True
    assert (await call(client, key, "projects_list"))["ok"]
    for path, credential in (("/ops/mcp/", key), ("/mcp/", ops_key)):
        for method, params in (
            (
                "initialize",
                {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            ),
            ("tools/list", {}),
            ("tools/call", {"name": "projects_list", "arguments": {}}),
        ):
            assert (await rpc(client, credential, method, params, path=path)).status_code == 403


async def test_ops_redirect_auth_and_origin(client, ops_key):
    assert (await client.post("/ops/mcp/", json={})).status_code == 401
    assert (await client.get("/ops/mcp/", headers=ROOT)).status_code == 401
    assert (await rpc(client, "invalid", "tools/list", path="/ops/mcp/")).status_code == 401
    _, scheduler = await issue(client, ["autohub:dispatch"])
    assert (await rpc(client, scheduler["key"], "tools/list", path="/ops/mcp/")).status_code == 403
    assert (await rpc(client, ops_key, "tools/list", path="/ops/mcp")).status_code == 200
    response = await client.post(
        "/ops/mcp/",
        headers=HEADERS | {"Authorization": f"Bearer {ops_key}", "Origin": "https://untrusted.example"},
        json={},
    )
    assert response.status_code == 403


async def test_options_independent_pages_and_explicit_mutation_inputs(client, key, ops_key):
    for name in ("First", "Second"):
        response = await client.post(
            "/api/v1/connectors",
            json={
                "name": name,
                "provider": "github",
                "credentials": {"token": "must-stay-private"},
            },
        )
        assert response.status_code == 201
    catalog = await client.post(
        "/api/v1/ai-catalogs",
        json={
            "key": "disabled-codex",
            "name": "Disabled Codex",
            "kind": "codex",
            "enabled": False,
        },
    )
    assert catalog.status_code == 201, catalog.text
    first = (
        await call(
            client,
            key,
            "projects_options",
            {
                "offset": 100,
                "connectors_page": {"limit": 1},
            },
        )
    )["result"]
    second = (
        await call(
            client,
            key,
            "projects_options",
            {
                "connectors_page": {"offset": 1, "limit": 1},
            },
        )
    )["result"]
    assert first["catalogs"]["items"] == []
    assert first["connectors"]["total_count"] == second["connectors"]["total_count"] == 2
    assert len(first["connectors"]["items"]) == len(second["connectors"]["items"]) == 1
    assert first["connectors"]["items"][0]["id"] != second["connectors"]["items"][0]["id"]
    assert "must-stay-private" not in str(first) + str(second)
    assert any(item["key"] == "disabled-codex" for item in second["catalogs"]["items"])
    enabled = (await call(client, key, "projects_options", {"enabled_only": True, "capability": "pipeline_delivery"}))[
        "result"
    ]
    assert all(item["enabled"] and item["pipeline_delivery"] for item in enabled["catalogs"]["items"])
    assert all(item["key"] != "disabled-codex" for item in enabled["catalogs"]["items"])
    for name, args, path, credential in (
        ("runs_enroll", {"project_id": str(uuid4()), "pull_request": {"pull_number": 7}}, "/mcp/", key),
        ("runs_resume", {"run_id": str(uuid4())}, "/mcp/", key),
        (
            "projects_create",
            {
                "project": {
                    "name": "Missing policy",
                    "github": {
                        "repository": "owner/new",
                        "github_connector_id": first["connectors"]["items"][0]["id"],
                        "verification": {"workflow": "ci.yml", "required_jobs": ["test"]},
                    },
                }
            },
            "/ops/mcp/",
            ops_key,
        ),
    ):
        denied = await call(client, credential, name, args, error=True, path=path)
        assert denied["error"]["code"] == "MCP_INVALID_ARGUMENTS"
    assert (await call(client, key, "projects_list"))["result"]["total_count"] == 0


async def test_project_preview_validates_and_apply_rejects_intervening_changes(client, key, ops_key):
    connector = await client.post(
        "/api/v1/connectors", json={"name": "GitHub", "provider": "github", "credentials": {"token": "test-only"}}
    )
    assert connector.status_code == 201
    config = {
        "name": "Preview",
        "github": {
            "repository": "owner/preview",
            "github_connector_id": connector.json()["id"],
            "verification": {"workflow": "ci.yml", "required_jobs": ["lint", "test"]},
            "automation": {"auto_merge": False},
        },
    }
    project = (await ops_call(client, ops_key, "projects_create", {"project": config}))["result"]
    target = {"project_id": project["id"]}
    changes = {"expected_revision": project["revision"], "github": {"verification": {"required_jobs": ["check"]}}}
    preview = (await ops_call(client, ops_key, "projects_update", target | {"project": changes, "dry_run": True}))[
        "result"
    ]
    assert preview["github"]["verification"]["required_jobs"] == ["check"]
    assert preview["changes"] == [
        {"path": "github.verification.required_jobs", "before": ["lint", "test"], "after": ["check"]}
    ]
    detached = (
        await ops_call(
            client,
            ops_key,
            "projects_update",
            target
            | {
                "project": {"expected_revision": project["revision"], "github": None},
                "dry_run": True,
            },
        )
    )["result"]
    assert detached["github"] is None and detached["applied"] is False
    persisted = (await call(client, key, "projects_get", target))["result"]
    assert persisted["github"] == project["github"] and persisted["revision"] == project["revision"]
    invalid = await ops_call(
        client,
        ops_key,
        "projects_update",
        target
        | {
            "project": {"expected_revision": project["revision"], "github": {"github_connector_id": str(uuid4())}},
            "dry_run": True,
        },
        error=True,
    )
    assert invalid["error"]["code"] == "INVALID_REQUEST"
    renamed = (
        await ops_call(
            client,
            ops_key,
            "projects_update",
            target
            | {
                "project": {"expected_revision": project["revision"], "name": "Concurrent edit"},
            },
        )
    )["result"]
    stale = await ops_call(client, ops_key, "projects_update", target | {"project": changes}, error=True)
    assert stale["error"]["code"] == "CONFLICT"
    current = (await call(client, key, "projects_get", target))["result"]
    assert current["name"] == renamed["name"]
    assert current["github"]["verification"]["required_jobs"] == ["lint", "test"]


async def test_connection_history_filters_and_paginates_only_recent_window(client, key, ops_key, session_maker):
    from app.features.project_management.connection_tests.models import ConnectionTest

    project = (await ops_call(client, ops_key, "projects_create", {"project": {"name": "History"}}))["result"]
    now = utc_now()
    ids = [uuid4() for _ in range(32)]
    async with session_maker() as session:
        for index, test_id in enumerate(ids):
            session.add(
                ConnectionTest(
                    id=test_id,
                    project_id=UUID(project["id"]),
                    project_revision=1,
                    repository="owner/history",
                    connector_id=uuid4(),
                    verification={},
                    created_at=now - timedelta(minutes=index),
                    deadline=now,
                    status="succeeded" if index % 2 == 0 else "failed",
                    phase="done",
                    cleanup_status="completed",
                )
            )
        await session.commit()
    target = {"project_id": project["id"]}
    page = (
        await call(
            client,
            key,
            "connection_tests_list",
            target
            | {
                "status": "succeeded",
                "configuration_current": False,
                "limit": 2,
            },
        )
    )["result"]
    assert page["total_count"] == 15 and page["history_limit"] == 30 and page["next_offset"] == 2
    assert [test["id"] for test in page["items"]] == [str(ids[0]), str(ids[2])]
    next_page = (
        await call(
            client,
            key,
            "connection_tests_list",
            target
            | {
                "status": "succeeded",
                "offset": page["next_offset"],
                "limit": 2,
            },
        )
    )["result"]
    assert [test["id"] for test in next_page["items"]] == [str(ids[4]), str(ids[6])]
    empty = (await call(client, key, "connection_tests_list", target | {"offset": 30}))["result"]
    assert empty["items"] == [] and empty["total_count"] == 30 and empty["next_offset"] is None
    old = (await call(client, key, "connection_tests_get", target | {"test_id": str(ids[31])}))["result"]
    assert old["id"] == str(ids[31])
