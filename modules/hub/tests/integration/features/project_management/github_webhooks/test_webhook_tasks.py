import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock

import httpx
import pytest
from app.common.config import GitHubWebhookConfig, get_github_webhook_config
from app.features.project_management.github_webhooks import tasks
from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.github_webhooks.usecases import GitHubWebhookUseCase
from pydantic import SecretStr
from sqlalchemy import select

pytestmark = pytest.mark.integration

SECRET = "webhook-test-secret"
QUEUE = "projects/p/locations/us-west1/queues/autohub-webhooks"


def config(**overrides) -> GitHubWebhookConfig:
    values = {
        "GITHUB_WEBHOOK_SECRET": SecretStr(SECRET),
        "WEBHOOK_TASK_QUEUE": QUEUE,
        "WEBHOOK_TASK_BASE_URL": "https://hub.example.com/",
    }
    return GitHubWebhookConfig(**{**values, **overrides})


def test_task_signature_is_bound_to_the_delivery_and_expires():
    expires = int(time.time()) + 60
    signature = tasks.sign(SECRET, "d-1", expires)

    assert tasks.verify(SECRET, "d-1", str(expires), signature)
    assert not tasks.verify(SECRET, "d-2", str(expires), signature)
    assert not tasks.verify("other-secret", "d-1", str(expires), signature)
    assert not tasks.verify(SECRET, "d-1", str(expires + 1), signature)
    assert not tasks.verify(SECRET, "d-1", None, signature)
    expired = int(time.time()) - 1
    assert not tasks.verify(SECRET, "d-1", str(expired), tasks.sign(SECRET, "d-1", expired))


@pytest.fixture
def cloud(monkeypatch):
    """Metadata server and Cloud Tasks API; `status` sets the task creation response."""
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.host == "metadata.google.internal":
            return httpx.Response(200, json={"access_token": "sa-token", "expires_in": 3599})
        return httpx.Response(respond.status, json={})

    respond.status = 200  # type: ignore[attr-defined]
    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(tasks, "get_http_client", lambda: client)
    monkeypatch.setattr(tasks, "_token", None)
    return respond, requests


async def test_enqueue_creates_a_signed_callback_task(cloud):
    _, requests = cloud

    assert await tasks.enqueue(config(), "d-1")

    metadata, create = requests
    assert metadata.headers["Metadata-Flavor"] == "Google"
    assert str(create.url) == f"https://cloudtasks.googleapis.com/v2/{QUEUE}/tasks"
    assert create.headers["Authorization"] == "Bearer sa-token"
    request = json.loads(create.content)["task"]["httpRequest"]
    assert request["url"] == "https://hub.example.com/api/github/webhooks/deliveries/d-1/process"
    headers = request["headers"]
    assert tasks.verify(SECRET, "d-1", headers[tasks.TASK_EXPIRES_HEADER], headers[tasks.TASK_SIGNATURE_HEADER])


async def test_enqueue_reports_an_unset_or_refusing_queue(cloud):
    respond, requests = cloud

    assert not await tasks.enqueue(config(WEBHOOK_TASK_QUEUE=None), "d-1")
    assert not requests
    respond.status = 403
    assert not await tasks.enqueue(config(), "d-1")


def _signed(body: bytes, delivery: str) -> dict[str, str]:
    return {
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest(),
        "Content-Type": "application/json",
    }


def _callback(delivery: str, secret: str = SECRET) -> dict[str, str]:
    expires = int(time.time()) + 60
    return {tasks.TASK_EXPIRES_HEADER: str(expires), tasks.TASK_SIGNATURE_HEADER: tasks.sign(secret, delivery, expires)}


@pytest.mark.parametrize("queued", [True, False])
async def test_a_queued_delivery_is_not_also_processed_in_the_background(client, monkeypatch, queued):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    get_github_webhook_config.cache_clear()
    monkeypatch.setattr(tasks, "enqueue", AsyncMock(return_value=queued))
    process = AsyncMock()
    monkeypatch.setattr(GitHubWebhookUseCase, "process", process)
    body = b'{"repository":{"full_name":"owner/repository"},"pull_request":{"number":3}}'

    response = await client.post("/api/github/webhooks", content=body, headers=_signed(body, f"queued-{queued}"))

    assert response.status_code == 202
    assert process.await_count == (0 if queued else 1)
    get_github_webhook_config.cache_clear()


async def test_the_callback_processes_a_stored_delivery_once(client, session, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    get_github_webhook_config.cache_clear()
    monkeypatch.setattr(tasks, "enqueue", AsyncMock(return_value=True))
    body = b'{"repository":{"full_name":"owner/repository"},"pull_request":{"number":3}}'
    assert (await client.post("/api/github/webhooks", content=body, headers=_signed(body, "cb-1"))).status_code == 202
    url = "/api/github/webhooks/deliveries/cb-1/process"

    assert (await client.post(url, headers=_callback("cb-1", "wrong"))).status_code == 401
    assert (await client.post(url, headers=_callback("cb-2"))).status_code == 401
    assert (await client.post(url, headers=_callback("cb-1"))).status_code == 204
    # Cloud Tasks delivers at least once.
    assert (await client.post(url, headers=_callback("cb-1"))).status_code == 204

    row = await session.scalar(select(GitHubWebhookDelivery).where(GitHubWebhookDelivery.delivery_id == "cb-1"))
    assert row is not None and (row.status, row.attempts) == ("processed", 1)
    get_github_webhook_config.cache_clear()
