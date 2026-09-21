from collections.abc import Sequence
from datetime import datetime

from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.projects.models import Project
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class GitHubWebhookRepository:
    async def create(self, session: AsyncSession, delivery: GitHubWebhookDelivery) -> GitHubWebhookDelivery:
        session.add(delivery)
        await session.flush()
        return delivery

    async def project_for_repository(self, session: AsyncSession, repository: str) -> Project | None:
        return await session.scalar(select(Project).where(Project.github_repository == repository.lower()))

    async def get(self, session: AsyncSession, delivery_id: str) -> GitHubWebhookDelivery | None:
        return await session.scalar(
            select(GitHubWebhookDelivery).where(GitHubWebhookDelivery.delivery_id == delivery_id)
        )

    async def list_stalled(
        self, session: AsyncSession, *, received_before: datetime, received_after: datetime, max_attempts: int
    ) -> Sequence[GitHubWebhookDelivery]:
        """Deliveries whose processing was lost, or whose `@auto-run` failed: polling recovers neither enrollment."""
        rows = await session.scalars(
            select(GitHubWebhookDelivery)
            .where(
                GitHubWebhookDelivery.created_at < received_before,
                GitHubWebhookDelivery.created_at > received_after,
                GitHubWebhookDelivery.attempts < max_attempts,
                or_(
                    GitHubWebhookDelivery.status == "received",
                    and_(GitHubWebhookDelivery.status == "failed", GitHubWebhookDelivery.auto_run.is_(True)),
                ),
            )
            .order_by(GitHubWebhookDelivery.created_at)
            .limit(20)
        )
        return rows.all()

    async def claim(self, session: AsyncSession, delivery: GitHubWebhookDelivery) -> bool:
        """Take a stalled delivery for replay; a concurrent sweep or a late first pass loses the claim."""
        result = await session.execute(
            update(GitHubWebhookDelivery)
            .where(
                GitHubWebhookDelivery.id == delivery.id,
                GitHubWebhookDelivery.status == delivery.status,
                GitHubWebhookDelivery.attempts == delivery.attempts,
            )
            .values(status="retrying")
        )
        return result.rowcount == 1  # type: ignore[attr-defined]

    async def delete_received_before(self, session: AsyncSession, received_before: datetime) -> None:
        """Drop old deliveries. The rows are also the deduplication keys, so the horizon must stay far beyond the
        few days in which GitHub redelivers."""
        await session.execute(delete(GitHubWebhookDelivery).where(GitHubWebhookDelivery.created_at < received_before))

    async def list(
        self,
        session: AsyncSession,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
        repository: str | None = None,
        noteworthy: bool = False,
    ) -> tuple[Sequence[GitHubWebhookDelivery], int]:
        """One page of deliveries, most recent first. ``noteworthy`` keeps those an operator would look for:
        triggers, and anything that failed or left a note."""
        matching = []
        if status is not None:
            matching.append(GitHubWebhookDelivery.status == status)
        if repository is not None:
            matching.append(GitHubWebhookDelivery.repository == repository.lower())
        if noteworthy:
            matching.append(
                or_(
                    GitHubWebhookDelivery.auto_run.is_(True),
                    GitHubWebhookDelivery.failure_detail.is_not(None),
                    GitHubWebhookDelivery.status != "processed",
                )
            )
        rows = await session.scalars(
            select(GitHubWebhookDelivery)
            .where(*matching)
            .order_by(GitHubWebhookDelivery.created_at.desc(), GitHubWebhookDelivery.id)
            .offset(offset)
            .limit(limit)
        )
        total = await session.scalar(select(func.count()).select_from(GitHubWebhookDelivery).where(*matching))
        return rows.all(), int(total or 0)
