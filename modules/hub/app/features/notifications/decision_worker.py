import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.notifications.decision_models import DecisionNotice
from app.features.notifications.decision_repo import DecisionNoticeRepository
from app.features.notifications.decision_service import DecisionNoticeService, aware, matches
from app.features.notifications.decision_transport import send_decision_message
from app.features.notifications.repos import NotificationChannelRepository
from app.features.notifications.services import NotificationChannelService
from app_http_client import get_http_client
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.core.log import logger
from app_layer_base.utils.time_util import get_current_utc_time


class DecisionNoticeWorker:
    def __init__(self, channels=None, transport=send_decision_message):
        self.repo = DecisionNoticeRepository()
        self.service = DecisionNoticeService()
        self.channels = channels
        self.transport = transport

    async def expire(self, session, channel_id):
        now = get_current_utc_time()
        for attempt in await self.repo.expired(session, channel_id, now):
            attempt.state, attempt.detail, attempt.outcome_at = "unknown", "lease-expired", now
            for id in attempt.notice_ids:
                notice = await self.repo.notice(session, channel_id, UUID(id))
                if notice and notice.last_attempt_id == attempt.id:
                    notice.state = "unknown"

    async def collect(self, channel_id):
        async with AsyncTransaction() as session:
            channel = await self.repo.channel(session, channel_id)
            if not channel:
                return None
            sub = await self.repo.subscription(session, channel_id)
            await self.expire(session, channel_id)
            if not self.service.enabled(channel, sub):
                return None
            known = await self.repo.generations(session, channel_id, channel.destination_generation)
            by_key = {(n.decision_key, n.fingerprint): n for n in known}
            rows = await self.repo.scan(session, sub)
            for entry, run, project in rows:
                if (
                    matches(entry, sub)
                    and (entry.key, entry.fingerprint) not in by_key
                    and not await self.repo.generation(
                        session, channel_id, channel.destination_generation, entry.key, entry.fingerprint
                    )
                ):
                    notice = DecisionNotice(
                        id=uuid4(),
                        channel_id=channel_id,
                        destination_generation=channel.destination_generation,
                        decision_key=entry.key,
                        fingerprint=entry.fingerprint,
                        state="pending",
                        observed={
                            "kind": entry.kind,
                            "project_name": project.name,
                            "run_id": str(run.id),
                            "pull_number": run.pull_number,
                            "waiting_since": entry.waiting_since.isoformat(),
                            "observed_at": entry.observed_at.isoformat(),
                        },
                    )
                    session.add(notice)
                    known.append(notice)
                    by_key[(entry.key, entry.fingerprint)] = notice
            if rows:
                sub.scan_time, sub.scan_key = rows[-1][0].waiting_since, rows[-1][0].key
            else:
                sub.scan_time = sub.scan_key = None
            pending = []
            for notice in known:
                if notice.state != "pending":
                    continue
                row = await self.repo.exact(session, notice.decision_key)
                if row and row[0].fingerprint == notice.fingerprint and matches(row[0], sub):
                    pending.append((notice, *row))
                else:
                    notice.state = "superseded"
            now = get_current_utc_time()
            if not pending:
                sub.digest_since = None
                return None
            if sub.digest_since is None:
                sub.digest_since = now
            if sub.settings["mode"] == "digest" and aware(sub.digest_since) + timedelta(minutes=15) > now:
                return None
            text, notices = self.service.message(pending, sub.settings["review_origin"])
            if not notices:
                return None
            attempt = self.service.admit(session, channel, notices, text)
            sub.digest_since = None
            await session.flush()
            return attempt.id

    async def deliver(self, attempt_id):
        # An admitted attempt is sent once by the admitting caller. Restart cannot prove non-delivery.
        async with AsyncTransaction() as session:
            attempt = await self.repo.attempt(session, attempt_id)
            if not attempt:
                return
            channel = await self.repo.channel(session, attempt.channel_id)
            if not channel or attempt.state != "sending" or aware(attempt.lease_expires_at) <= get_current_utc_time():
                return
            token, text = attempt.token, attempt.message
            chat_id = (channel.config or {}).get("chat_id")
            # A post-admission rotation must not send to a newly configured destination.
            if channel.destination_generation != attempt.destination_generation:
                outcome, detail = "failed", "destination-rotated"
                bot = None
            else:
                try:
                    channels = self.channels or NotificationChannelService(
                        NotificationChannelRepository(), ConnectorCredentialCipher(get_credential_key_provider())
                    )
                    bot = await channels.bot_token(channel)
                except ValueError:
                    bot = None
                outcome, detail = "failed", "missing-destination"
        if bot:
            outcome, detail = await self.transport(get_http_client(), bot, chat_id, text)
        async with AsyncTransaction() as session:
            attempt = await self.repo.attempt(session, attempt_id)
            if not attempt:
                return
            channel = await self.repo.channel(session, attempt.channel_id)
            if (
                not channel
                or attempt.state != "sending"
                or attempt.token != token
                or aware(attempt.lease_expires_at) <= get_current_utc_time()
            ):
                return
            attempt.state, attempt.detail, attempt.outcome_at = outcome, detail, get_current_utc_time()
            for id in attempt.notice_ids:
                notice = await self.repo.notice(session, channel.id, UUID(id))
                if notice and notice.last_attempt_id == attempt.id:
                    notice.state = outcome
            await self.repo.compact(session, channel.id)

    async def tick(self):
        async with asyncio.timeout(45):
            async with AsyncTransaction() as session:
                ids = await self.repo.next_channels(session)
            for channel_id in ids:
                try:
                    id = await self.collect(channel_id)
                    if id:
                        await self.deliver(id)
                except Exception:
                    logger.exception("Decision notice maintenance will retain unresolved delivery")
