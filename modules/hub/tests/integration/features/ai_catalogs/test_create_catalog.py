from uuid import uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog
from sqlalchemy import select

from tests.integration.features.ai_catalogs.test_ai_catalogs_api import connector
from tests.utils.assertions import assert_status_code

URL = "/api/v1/ai-catalogs"


def payload(**overrides):
    return {"key": "team-codex", "name": "Team Codex", "kind": "codex", **overrides}


async def test_create_codex_defaults_list_and_disable(client):
    response = await client.post(URL, json=payload(configured_concurrency=4))
    assert_status_code(response, 201)
    catalog = response.json()
    assert catalog["adapter"] == "codex-github-mention"
    assert catalog["pipeline_delivery"] is True
    assert catalog["session_work_types"] == []
    assert catalog["connector_id"] is None
    assert catalog["configured_concurrency"] == catalog["effective_concurrency"] == 4
    assert catalog["policy_config"]["short_refresh_enabled"] is True
    assert catalog["active_dispatch_count"] == 0
    assert catalog["revision"] == 1
    listed = (await client.get(URL)).json()["items"]
    assert next(row for row in listed if row["id"] == catalog["id"]) == catalog
    disabled = await client.put(URL + "/team-codex/enabled", json={"enabled": False})
    assert_status_code(disabled, 200)
    assert disabled.json()["availability_state"] == "disabled"


async def test_create_jules_with_connector_and_custom_quota(client, session):
    key = connector("Team Jules key", "jules")
    session.add(key)
    await session.commit()
    response = await client.post(
        URL,
        json=payload(
            key="team-jules",
            name=" Team Jules ",
            kind="jules",
            connector_id=str(key.id),
            configured_concurrency=2,
            policy_config={"daily_task_limit": 25},
            enabled=False,
        ),
    )
    assert_status_code(response, 201)
    data = response.json()
    assert data["name"] == "Team Jules"
    assert data["adapter"] == "jules-api"
    assert data["connector_id"] == str(key.id)
    assert data["connector_provider"] == "jules"
    assert data["session_work_types"] == ["task", "report"]
    assert data["pipeline_delivery"] is False
    assert data["availability_state"] == "disabled"
    assert data["policy_config"] == {"daily_task_limit": 25, "window": "rolling", "timezone": "UTC"}


async def test_jules_can_be_created_before_credentials_are_registered(client):
    response = await client.post(URL, json=payload(kind="jules", policy_config={"daily_task_limit": 3}))
    assert_status_code(response, 201)
    assert response.json()["connector_id"] is None


async def test_duplicate_key_does_not_replace_existing_catalog(client):
    original = (await client.post(URL, json=payload())).json()
    duplicate = await client.post(URL, json=payload(name="Replacement", configured_concurrency=99))
    assert_status_code(duplicate, 409)
    assert (await client.get(URL)).json()["items"] == [original]
    assert_status_code(await client.post(URL, json=payload(key="another-codex")), 201)


@pytest.mark.parametrize(
    "fields",
    [
        {"key": "bad/key"},
        {"key": "Uppercase"},
        {"key": ""},
        {"name": "   "},
        {"kind": "unknown"},
        {"configured_concurrency": 0},
        {"configured_concurrency": 1001},
        {"adapter": "jules-api"},
        {"policy_state": {"remaining": 100}},
        {"kind": "jules"},
        {"kind": "jules", "policy_config": {"daily_task_limit": 0}},
        {"policy_config": {"daily_task_limit": 10}},
        {"connector_id": str(uuid4())},
    ],
)
async def test_invalid_creation_is_atomic(client, session, fields):
    response = await client.post(URL, json=payload(**fields))
    assert_status_code(response, 422)
    assert (await session.scalars(select(AICatalog))).all() == []


@pytest.mark.parametrize("provider,enabled", [("github", True), ("jules", False), (None, True)])
async def test_jules_rejects_wrong_disabled_or_missing_connector(client, session, provider, enabled):
    connector_id = uuid4()
    if provider:
        key = connector("Wrong key", provider)
        key.enabled = enabled
        session.add(key)
        await session.commit()
        connector_id = key.id
    response = await client.post(
        URL,
        json=payload(
            kind="jules",
            connector_id=str(connector_id),
            policy_config={"daily_task_limit": 3},
        ),
    )
    assert_status_code(response, 422)
    assert (await session.scalars(select(AICatalog))).all() == []
