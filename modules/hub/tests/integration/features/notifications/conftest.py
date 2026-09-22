import json

import httpx
import pytest
from app.features.notifications import notifier
from app.features.notifications.telegram import TELEGRAM_API_BASE_URL


class FakeTelegram:
    def __init__(self) -> None:
        self.response: tuple[int, dict] = (200, {"ok": True})
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.response
        return httpx.Response(status, json=body)

    @property
    def texts(self) -> list[str]:
        return [json.loads(request.content)["text"] for request in self.requests]


@pytest.fixture
def telegram(monkeypatch) -> FakeTelegram:
    fake = FakeTelegram()
    monkeypatch.setattr(
        notifier,
        "create_telegram_client",
        lambda: httpx.AsyncClient(base_url=TELEGRAM_API_BASE_URL, transport=httpx.MockTransport(fake.handle)),
    )
    return fake


@pytest.fixture
async def channel(client) -> dict:
    response = await client.post(
        "/api/v1/notification-channels",
        json={"name": "My phone", "chat_id": "424242", "bot_token": "123:bot-secret"},
    )
    assert response.status_code == 201, response.text
    return response.json()
