from typing import Annotated

from app.features.project_management.github_webhooks.repos import GitHubWebhookRepository
from app.features.project_management.github_webhooks.schemas import (
    GitHubWebhookDeliveryList,
    GitHubWebhookDeliveryRead,
    WebhookDeliveryStatus,
)
from app_layer_base.core.database.transaction import AsyncTransaction
from fastapi import Depends


class GitHubWebhookDeliveryQueries:
    """Read side of the delivery log; receiving and processing live in ``usecases``."""

    def __init__(self, repo: Annotated[GitHubWebhookRepository, Depends()]) -> None:
        self.repo = repo

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        status: WebhookDeliveryStatus | None,
        repository: str | None,
        noteworthy: bool,
    ) -> GitHubWebhookDeliveryList:
        async with AsyncTransaction() as session:
            rows, total = await self.repo.list(
                session, offset=offset, limit=limit, status=status, repository=repository, noteworthy=noteworthy
            )
            return GitHubWebhookDeliveryList(
                items=[GitHubWebhookDeliveryRead.model_validate(row) for row in rows], total_count=total
            )
