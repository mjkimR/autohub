from typing import Annotated

from app.features.project_management.github_webhooks.queries import GitHubWebhookDeliveryQueries
from app.features.project_management.github_webhooks.schemas import GitHubWebhookDeliveryList, WebhookDeliveryStatus
from fastapi import APIRouter, Depends, Query

# Read-only and behind the API key, unlike the receiving endpoint that GitHub signs.
router = APIRouter(prefix="/github-webhook-deliveries", tags=["GitHub Webhook"])


@router.get("", response_model=GitHubWebhookDeliveryList)
async def list_github_webhook_deliveries(
    queries: Annotated[GitHubWebhookDeliveryQueries, Depends()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    status: WebhookDeliveryStatus | None = None,
    repository: str | None = None,
    noteworthy: bool = False,
):
    """The delivery log: what GitHub sent, what it triggered, and why a trigger did not enroll or dispatch."""
    return await queries.list(offset=offset, limit=limit, status=status, repository=repository, noteworthy=noteworthy)
