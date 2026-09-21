import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.github_webhooks.repos import GitHubWebhookRepository
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import EnrollPullRequest
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.projects.services import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy.exc import IntegrityError

# A delivery still unhandled after this long lost its background processing (the instance was stopped or throttled).
STALLED_DELIVERY_AGE = timedelta(minutes=2)
# Older deliveries are history, not work: replaying a day-old trigger would surprise more than help.
STALLED_DELIVERY_HORIZON = timedelta(hours=24)
# The first pass and one replay.
MAX_DELIVERY_ATTEMPTS = 2


@dataclass(frozen=True)
class DeliveryFacts:
    """Everything processing reads from a payload."""

    repository: str | None
    pull_number: int | None
    auto_run: bool
    catalog: str | None

    @classmethod
    def of(cls, event: str | None, payload: dict[str, Any]) -> "DeliveryFacts":
        trigger_text = _extract_trigger_text(event, payload)
        trigger = AUTO_RUN_TRIGGER.search(trigger_text) if trigger_text else None
        return cls(
            repository=_repository(payload),
            pull_number=_pull_number(payload),
            auto_run=trigger is not None,
            catalog=trigger.group("catalog") if trigger is not None else None,
        )


# `@auto-run` enrolls the pull request; `@auto-run:<catalog key or kind>` also names the catalog that delivers it.
AUTO_RUN_TRIGGER = re.compile(r"@auto-run(?::(?P<catalog>[A-Za-z0-9_.-]+))?\b", re.IGNORECASE)


class GitHubWebhookUseCase:
    def __init__(self, repo: GitHubWebhookRepository, runs: PipelineRunRepository, lifecycle: PipelineRunUseCase):
        self.repo = repo
        self.runs = runs
        self.lifecycle = lifecycle

    @staticmethod
    def verify_signature(secret: str, raw_body: bytes, signature: str | None) -> bool:
        expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return signature is not None and hmac.compare_digest(signature, expected)

    async def receive(self, delivery_id: str, event: str, raw_body: bytes, payload: dict[str, Any]) -> bool:
        facts = DeliveryFacts.of(event, payload)
        try:
            async with AsyncTransaction() as session:
                await self.repo.create(
                    session,
                    GitHubWebhookDelivery(
                        delivery_id=delivery_id,
                        event=event,
                        repository=facts.repository,
                        payload_digest=hashlib.sha256(raw_body).hexdigest(),
                        pull_number=facts.pull_number,
                        auto_run=facts.auto_run,
                        requested_catalog=facts.catalog[:255] if facts.catalog else None,
                    ),
                )
        except IntegrityError:
            # GitHub retries the same delivery ID; never re-run an external action.
            return False
        return True

    async def process(self, delivery_id: str, payload: dict[str, Any], event: str | None = None) -> None:
        """Advance the matching active run, or enroll a new run if @auto-run is mentioned."""
        await self._handle(delivery_id, DeliveryFacts.of(event, payload))

    async def sweep_stalled(self, now: datetime) -> list[str]:
        """Replay deliveries whose processing was lost, and failed `@auto-run` triggers, once each.

        Polling already recovers a missed advance, but nothing else would ever enroll a missed `@auto-run`.
        Returns a notice for each trigger that still could not be handled.
        """
        async with AsyncTransaction() as session:
            stalled = [
                (row, DeliveryFacts(row.repository, row.pull_number, row.auto_run, row.requested_catalog))
                for row in await self.repo.list_stalled(
                    session,
                    received_before=now - STALLED_DELIVERY_AGE,
                    received_after=now - STALLED_DELIVERY_HORIZON,
                    max_attempts=MAX_DELIVERY_ATTEMPTS,
                )
            ]
            claimed = [(row.delivery_id, facts) for row, facts in stalled if await self.repo.claim(session, row)]
        notices = []
        for delivery_id, facts in claimed:
            if not await self._handle(delivery_id, facts) and facts.auto_run:
                notices.append(
                    f"An @auto-run on {facts.repository}#{facts.pull_number} could not be handled after a retry. "
                    "Enroll the pull request from the hub."
                )
        return notices

    async def _handle(self, delivery_id: str, facts: DeliveryFacts) -> bool:
        """Process one delivery from its facts; False when processing failed."""
        try:
            repository, pull_number, has_trigger, catalog = (
                facts.repository,
                facts.pull_number,
                facts.auto_run,
                facts.catalog,
            )
            if repository is None:
                await self._finish(delivery_id, "processed")
                return True

            async with AsyncTransaction() as session:
                project = await self.repo.project_for_repository(session, repository)
                run = (
                    await self.runs.get_active_for_pull(session, project.id, pull_number)
                    if project is not None and pull_number is not None
                    else None
                )

            if run is not None:
                await self.lifecycle.manual_advance(run.id, self.lifecycle.observer)
            elif (
                has_trigger
                and project is not None
                and project.enabled
                and project.automation.get("auto_enroll_on_trigger", True)
                and pull_number is not None
            ):
                try:
                    new_run = await self.lifecycle.enroll(
                        project.id, EnrollPullRequest(pull_number=pull_number, catalog=catalog)
                    )
                except ProjectError as exc:
                    # e.g. concurrent enrollment, already enrolled, or a catalog that cannot take the work.
                    # The delivery is still processed; the reason is kept where operators can find it.
                    await self._finish(delivery_id, "processed", f"Enrollment skipped: {exc.detail}")
                    return True
                try:
                    await self.lifecycle.manual_advance(new_run.id, self.lifecycle.observer)
                except ProjectError as exc:
                    # The run exists; the scheduler dispatches it once the reason (a quota hold, say) clears.
                    await self._finish(delivery_id, "processed", f"Enrolled; first dispatch deferred: {exc.detail}")
                    return True

            await self._finish(delivery_id, "processed")
            return True
        except Exception:
            # Delivery endpoints must acknowledge authenticated GitHub events; polling recovers a failed advance
            # and the sweep retries a failed @auto-run.
            logger.exception(f"Processing GitHub webhook delivery {delivery_id} failed")
            await self._finish(delivery_id, "failed", "Webhook processing failed")
            return False

    async def _finish(self, delivery_id: str, status: str, failure_detail: str | None = None) -> None:
        async with AsyncTransaction() as session:
            delivery = await self.repo.get(session, delivery_id)
            if delivery is not None:
                delivery.status = status
                delivery.attempts += 1
                delivery.processed_at = get_current_utc_time()
                delivery.failure_detail = failure_detail
                await session.flush()


def _repository(payload: dict[str, Any]) -> str | None:
    value = payload.get("repository", {}).get("full_name")
    return value.lower() if isinstance(value, str) and value else None


def _pull_number(payload: dict[str, Any]) -> int | None:
    for key in ("pull_request", "issue"):
        number = payload.get(key, {}).get("number")
        if isinstance(number, int) and number > 0:
            return number
    pulls = payload.get("workflow_run", {}).get("pull_requests")
    if isinstance(pulls, list) and len(pulls) == 1:
        number = pulls[0].get("number") if isinstance(pulls[0], dict) else None
        if isinstance(number, int) and number > 0:
            return number
    return None


def _extract_trigger_text(event: str | None, payload: dict[str, Any]) -> str | None:
    action = payload.get("action")
    # PR opened or reopened (or without action field in test mocks)
    if (
        event == "pull_request" or (event is None and "pull_request" in payload and "comment" not in payload)
    ) and action in (
        "opened",
        "reopened",
        None,
    ):
        body = payload.get("pull_request", {}).get("body")
        return body if isinstance(body, str) else None

    # Issue comment created on a pull request (or without action field in test mocks)
    if (
        (event == "issue_comment" or (event is None and "comment" in payload))
        and action in ("created", None)
        and "pull_request" in payload.get("issue", {})
    ):
        body = payload.get("comment", {}).get("body")
        return body if isinstance(body, str) else None

    return None
