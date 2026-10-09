import pytest
from app.features.execution.flows.auth import get_flow_principal
from app_layer_base.core.database.deps import get_session
from tests.integration.features.execution.flows.test_host import RELEASE_PATH, RUNS, inputs, release

pytestmark = pytest.mark.real_commit
ROOT = {"X-Root-API-Key": "root-test-credential-at-least-32-characters"}


async def machine(client, name, scopes):
    created = await client.post("/api/v1/machines", headers=ROOT, json={"name": name, "scopes": scopes})
    assert created.status_code == 201, created.text
    identity = created.json()["id"]
    key = await client.post(f"/api/v1/machines/{identity}/keys", headers=ROOT, json={"label": "test"})
    assert key.status_code == 201, key.text
    return {"X-API-Key": key.json()["key"]}


async def test_real_machine_key_and_revocation_guard_sdk_routes(client, app, session_maker):
    async def fresh_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = fresh_session
    app.dependency_overrides.pop(get_flow_principal, None)
    assert (await client.post(RUNS, json=inputs())).status_code == 401
    scheduler = await machine(client, "scheduler", ["autohub:dispatch"])
    assert (
        await client.put(RELEASE_PATH, headers=scheduler, json=release().model_dump(mode="json"))
    ).status_code == 403
    owner = await machine(client, "planhub", ["autohub:task:read", "autohub:task:write", "autohub:task:approve"])
    assert (await client.put(RELEASE_PATH, headers=owner, json=release().model_dump(mode="json"))).status_code == 200
    assert (
        await client.post(RELEASE_PATH + "/activate", headers=owner, json={"expected_revision": 0})
    ).status_code == 200
    assert (await client.post(RUNS, headers=owner, json=inputs())).status_code == 202
    machines = (await client.get("/api/v1/machines", headers=ROOT)).json()
    identity = next(row["id"] for row in machines if row["name"] == "planhub")
    keys = (await client.get(f"/api/v1/machines/{identity}/keys", headers=ROOT)).json()
    response = await client.delete(f"/api/v1/machines/{identity}/keys/{keys[0]['id']}", headers=ROOT)
    assert response.status_code == 200, response.text
    assert (await client.post(RUNS, headers=owner, json=inputs())).status_code == 401
