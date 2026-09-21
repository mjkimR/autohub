import json
from uuid import UUID

import pytest
from app.features.notifications.models import NotificationChannel

from tests.utils.assertions import assert_status_code

pytestmark = pytest.mark.e2e

ROOT = "/api/v1/notification-channels"


async def test_a_channel_seals_its_bot_token_and_never_returns_it(client, session, channel):
    assert (channel["name"], channel["kind"], channel["chat_id"], channel["enabled"], channel["min_level"]) == (
        "My phone",
        "telegram",
        "424242",
        True,
        "info",
    )
    assert "bot_token" not in channel and "bot-secret" not in json.dumps(channel)
    stored = await session.get(NotificationChannel, UUID(channel["id"]))
    assert stored is not None and b"bot-secret" not in stored.credentials_ciphertext

    listed = await client.get(ROOT)
    assert_status_code(listed, 200)
    assert [item["id"] for item in listed.json()["items"]] == [channel["id"]]
    assert "bot-secret" not in listed.text

    duplicate = await client.post(ROOT, json={"name": "My phone", "chat_id": "1", "bot_token": "t"})
    assert_status_code(duplicate, 409)


async def test_a_test_notice_goes_to_the_channel_even_when_disabled(client, channel, telegram):
    assert_status_code(await client.patch(f"{ROOT}/{channel['id']}", json={"enabled": False}), 200)

    result = await client.post(f"{ROOT}/{channel['id']}/test")

    assert_status_code(result, 200)
    assert result.json() == {"delivered": True, "detail": None}
    [request] = telegram.requests
    assert request.url.path == "/bot123:bot-secret/sendMessage"
    assert json.loads(request.content)["chat_id"] == "424242"
    [listed] = (await client.get(ROOT)).json()["items"]
    assert listed["last_sent_at"] is not None and listed["last_error"] is None


async def test_a_refused_notice_is_reported_and_kept_without_the_token(client, channel, telegram):
    telegram.response = (400, {"ok": False, "description": "Bad Request: chat not found"})

    result = await client.post(f"{ROOT}/{channel['id']}/test")

    assert result.json() == {"delivered": False, "detail": "Telegram returned HTTP 400: Bad Request: chat not found"}
    [listed] = (await client.get(ROOT)).json()["items"]
    assert listed["last_error"] == "Telegram returned HTTP 400: Bad Request: chat not found"
    assert listed["last_sent_at"] is None


async def test_a_rotated_token_and_chat_are_used_by_the_next_notice(client, channel, telegram):
    patched = await client.patch(f"{ROOT}/{channel['id']}", json={"chat_id": "-100777", "bot_token": "999:new"})
    assert_status_code(patched, 200)
    assert patched.json()["chat_id"] == "-100777"

    await client.post(f"{ROOT}/{channel['id']}/test")

    [request] = telegram.requests
    assert request.url.path == "/bot999:new/sendMessage"
    assert json.loads(request.content)["chat_id"] == "-100777"


async def test_a_deleted_or_unknown_channel_is_not_found(client, channel):
    assert_status_code(await client.delete(f"{ROOT}/{channel['id']}"), 204)
    assert_status_code(await client.post(f"{ROOT}/{channel['id']}/test"), 404)
    assert_status_code(await client.patch(f"{ROOT}/{channel['id']}", json={"enabled": True}), 404)
    assert (await client.get(ROOT)).json()["items"] == []


async def test_channel_min_level_can_be_customized_and_filters_broadcasts(
    client, channel, telegram, credential_key_provider
):
    assert channel["min_level"] == "info"

    patched = await client.patch(f"{ROOT}/{channel['id']}", json={"min_level": "error"})
    assert_status_code(patched, 200)
    assert patched.json()["min_level"] == "error"

    created = await client.post(
        ROOT,
        json={"name": "Second channel", "chat_id": "888888", "bot_token": "token2", "min_level": "warning"},
    )
    assert_status_code(created, 201)

    from app.features.configuration.connectors.crypto import ConnectorCredentialCipher
    from app.features.notifications.notifier import Notifier
    from app.features.notifications.repos import NotificationChannelRepository
    from app.features.notifications.services import NotificationChannelService

    notifier = Notifier(
        NotificationChannelService(
            NotificationChannelRepository(),
            ConnectorCredentialCipher(credential_key_provider),
        )
    )

    telegram.requests.clear()
    await notifier.send("Informational event", level="info")
    assert telegram.requests == []

    telegram.requests.clear()
    await notifier.send("Warning event", level="warning")
    assert len(telegram.requests) == 1
    assert json.loads(telegram.requests[0].content)["chat_id"] == "888888"
    assert "⚠️ [WARNING] Warning event" in telegram.texts

    telegram.requests.clear()
    await notifier.send("Error event", level="error")
    assert len(telegram.requests) == 2
    chat_ids = {json.loads(req.content)["chat_id"] for req in telegram.requests}
    assert chat_ids == {"424242", "888888"}
    assert all("🚨 [ERROR] Error event" in t for t in telegram.texts)

    telegram.requests.clear()
    test_res = await client.post(f"{ROOT}/{channel['id']}/test")
    assert_status_code(test_res, 200)
    assert len(telegram.requests) == 1
    assert json.loads(telegram.requests[0].content)["chat_id"] == "424242"
