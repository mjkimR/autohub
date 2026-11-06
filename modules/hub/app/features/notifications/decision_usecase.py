from typing import Annotated
from uuid import UUID

from app.features.notifications.decision_models import DecisionNoticeRequest, DecisionSubscription
from app.features.notifications.decision_repo import DecisionNoticeRepository
from app.features.notifications.decision_schemas import (
    DecisionRequestRead,
    NoticeAttemptRead,
    NoticeHistory,
    NoticeRead,
    SubscriptionSettings,
    SubscriptionWrite,
)
from app.features.notifications.decision_service import (
    DecisionNoticeService,
    command_digest,
    matches,
    subscription_read,
)
from app.features.notifications.services import NotificationChannelService
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends


class DecisionNoticeUseCase:
    def __init__(
        self,
        repo: Annotated[DecisionNoticeRepository, Depends()],
        channels: Annotated[NotificationChannelService, Depends()],
    ):
        self.repo = repo
        self.channels = channels
        self.service = DecisionNoticeService()

    async def _context(self, session, channel_id):
        channel = self.service.require_channel(await self.repo.channel(session, channel_id))
        return channel, await self.repo.subscription(session, channel_id)

    async def read(self, channel_id):
        async with AsyncTransaction() as session:
            channel, sub = await self._context(session, channel_id)
            return subscription_read(channel, sub)

    async def _result(self, session, channel, sub, operation, request_id, actor):
        receipt = await self.repo.request(session, channel.id, operation, request_id)
        if receipt and receipt.actor != actor:
            raise ProjectError(404, "Request not found")
        attempt = None
        if receipt and receipt.result.get("attempt_id"):
            attempt = await self.repo.attempt(session, UUID(receipt.result["attempt_id"]))
        return DecisionRequestRead(
            record_state="recorded" if receipt else "unknown",
            operation=operation,
            request_id=request_id,
            result=receipt.result if receipt else None,
            current=subscription_read(channel, sub),
            attempt=NoticeAttemptRead.model_validate(attempt) if attempt else None,
        )

    async def request(self, channel_id, operation, request_id, actor):
        async with AsyncTransaction() as session:
            channel, sub = await self._context(session, channel_id)
            return await self._result(session, channel, sub, operation, request_id, actor)

    async def save(self, channel_id, data: SubscriptionWrite, actor):
        async with AsyncTransaction() as session:
            channel, sub = await self._context(session, channel_id)
            digest = command_digest(data)
            receipt = await self.repo.request(session, channel_id, "subscription", data.request_id)
            if receipt:
                if receipt.actor != actor or receipt.digest != digest:
                    raise ProjectError(
                        409, "Request identity belongs to another command", code="DECISION_NOTICE_IDENTITY_CONFLICT"
                    )
            else:
                self.service.validate_basis(channel, sub, data)
                if not await self.repo.projects_exist(session, data.project_ids):
                    raise ProjectError(404, "Selected project not found")
                if sub is None:
                    sub = DecisionSubscription(channel_id=channel_id, revision=0, enabled=False, settings={})
                    session.add(sub)
                sub.revision += 1
                sub.enabled = data.enabled
                sub.settings = SubscriptionSettings.model_validate(
                    data.model_dump(exclude={"request_id", "expected_revision", "expected_destination_generation"})
                ).model_dump(mode="json")
                sub.scan_time = sub.scan_key = sub.digest_since = None
                session.add(
                    DecisionNoticeRequest(
                        channel_id=channel_id,
                        operation="subscription",
                        request_id=data.request_id,
                        actor=actor,
                        digest=digest,
                        result={
                            "revision": sub.revision,
                            "destination_generation": channel.destination_generation,
                            "settings": sub.settings,
                        },
                    )
                )
                await session.flush()
            return await self._result(session, channel, sub, "subscription", data.request_id, actor)

    async def history(self, channel_id, cursor, limit):
        async with AsyncTransaction() as session:
            await self._context(session, channel_id)
            rows, attempts = await self.repo.history(session, channel_id, cursor, limit)
            more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = f"{rows[-1].created_at.isoformat()}|{rows[-1].id}" if more and rows else None
            return NoticeHistory(
                items=[NoticeRead.model_validate(r) for r in rows],
                attempts=[NoticeAttemptRead.model_validate(r) for r in attempts],
                has_more=more,
                next_cursor=next_cursor,
                observed_at=get_current_utc_time(),
            )

    async def resend(self, channel_id, notice_id, data, actor):
        result, admitted = await self._resend(channel_id, notice_id, data, actor)
        if admitted:
            from .decision_worker import DecisionNoticeWorker

            await DecisionNoticeWorker(self.channels).deliver(admitted)
            return await self.request(channel_id, "resend", data.request_id, actor)
        return result

    async def _resend(self, channel_id, notice_id, data, actor):
        async with AsyncTransaction() as session:
            channel, sub = await self._context(session, channel_id)
            digest = command_digest(data, notice_id)
            receipt = await self.repo.request(session, channel_id, "resend", data.request_id)
            if receipt:
                if receipt.actor != actor or receipt.digest != digest:
                    raise ProjectError(
                        409, "Request identity belongs to another command", code="DECISION_NOTICE_IDENTITY_CONFLICT"
                    )
            else:
                self.service.validate_basis(channel, sub, data)
                if not self.service.enabled(channel, sub):
                    raise ProjectError(409, "Decision subscription is not effectively enabled")
                notice = await self.repo.notice(session, channel_id, notice_id)
                if not notice:
                    raise ProjectError(404, "Notice not found")
                if notice.state == "sending":
                    raise ProjectError(409, "An admitted message may still finish")
                if notice.state == "unknown" and not data.acknowledge_possible_duplicate:
                    raise ProjectError(409, "Acknowledge possible external duplicate before resending")
                row = await self.repo.exact(session, notice.decision_key)
                if (
                    notice.destination_generation != channel.destination_generation
                    or not row
                    or row[0].fingerprint != notice.fingerprint
                    or not matches(row[0], sub)
                ):
                    raise ProjectError(409, "Notice subject or subscription changed; open the current inbox")
                message, included = self.service.message([(notice, *row)], sub.settings["review_origin"])
                if not included:
                    raise ProjectError(409, "Notice metadata exceeds message limit")
                attempt = self.service.admit(session, channel, included, message)
                session.add(
                    DecisionNoticeRequest(
                        channel_id=channel_id,
                        operation="resend",
                        request_id=data.request_id,
                        actor=actor,
                        digest=digest,
                        result={
                            "notice_id": str(notice.id),
                            "attempt_id": str(attempt.id),
                            "destination_generation": channel.destination_generation,
                        },
                    )
                )
                await session.flush()
            return await self._result(
                session, channel, sub, "resend", data.request_id, actor
            ), attempt.id if not receipt else None
