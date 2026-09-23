"""Hand a received delivery to Cloud Tasks so it is processed in a request of its own.

Cloud Run with request-based billing barely allocates CPU after a response is sent, which is where in-process
background tasks run. A task calls back into the service, and that request gets CPU. The callback is authenticated
with an HMAC derived from the webhook secret: it names a delivery that was already verified and stored, and
processing a stored delivery twice is harmless, so no separate credential needs provisioning.
"""

import hashlib
import hmac
import time
from urllib.parse import quote

from app.common.config import GitHubWebhookConfig
from app_http_client import get_http_client
from app_layer_base.core.log import logger

TASK_SIGNATURE_HEADER = "X-Autohub-Task-Signature"
TASK_EXPIRES_HEADER = "X-Autohub-Task-Expires"
# Cloud Tasks retries within this window; a leaked signature is useless afterwards.
SIGNATURE_LIFETIME_SECONDS = 3600
# GitHub gives up on a delivery after 10 seconds; queueing must leave room for the fallback.
ENQUEUE_TIMEOUT_SECONDS = 4
# Leaves the processing request room under the service's 60-second request timeout.
DISPATCH_DEADLINE = "60s"
METADATA_TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
TASKS_API = "https://cloudtasks.googleapis.com/v2"

_token: tuple[str, float] | None = None


def task_path(delivery_id: str) -> str:
    return f"/api/github/webhooks/deliveries/{quote(delivery_id, safe='')}/process"


def sign(secret: str, delivery_id: str, expires: int) -> str:
    # A distinct message domain from GitHub's own body signatures made with the same secret.
    message = f"autohub-webhook-task\n{delivery_id}\n{expires}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify(secret: str, delivery_id: str, expires: str | None, signature: str | None) -> bool:
    if not expires or not signature or not expires.isdigit() or int(expires) < time.time():
        return False
    return hmac.compare_digest(signature, sign(secret, delivery_id, int(expires)))


async def _access_token() -> str:
    """The runtime service account's token from the Cloud Run metadata server, reused until shortly before expiry."""
    global _token
    if _token is not None and _token[1] > time.monotonic():
        return _token[0]
    response = await get_http_client().get(
        METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"}, timeout=ENQUEUE_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()
    _token = (data["access_token"], time.monotonic() + int(data["expires_in"]) - 60)
    return _token[0]


async def enqueue(config: GitHubWebhookConfig, delivery_id: str) -> bool:
    """Queue processing of a stored delivery; False when the queue is unset or did not accept it."""
    if not config.WEBHOOK_TASK_QUEUE or not config.WEBHOOK_TASK_BASE_URL or config.GITHUB_WEBHOOK_SECRET is None:
        return False
    expires = int(time.time()) + SIGNATURE_LIFETIME_SECONDS
    task = {
        "httpRequest": {
            "httpMethod": "POST",
            "url": config.WEBHOOK_TASK_BASE_URL.rstrip("/") + task_path(delivery_id),
            "headers": {
                TASK_EXPIRES_HEADER: str(expires),
                TASK_SIGNATURE_HEADER: sign(config.GITHUB_WEBHOOK_SECRET.get_secret_value(), delivery_id, expires),
            },
        },
        "dispatchDeadline": DISPATCH_DEADLINE,
    }
    try:
        response = await get_http_client().post(
            f"{TASKS_API}/{config.WEBHOOK_TASK_QUEUE}/tasks",
            json={"task": task},
            headers={"Authorization": f"Bearer {await _access_token()}"},
            timeout=ENQUEUE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        # An unconfirmed creation may still run; processing a delivery twice is harmless.
        logger.warning(f"Queueing webhook delivery {delivery_id} failed; processing in the background: {exc!r}")
        return False
