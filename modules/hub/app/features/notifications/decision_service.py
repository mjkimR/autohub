import hashlib
import json
from datetime import UTC, timedelta
from urllib.parse import urlencode
from uuid import uuid4

from app.features.notifications.decision_models import DecisionNoticeAttempt
from app.features.notifications.decision_schemas import SubscriptionRead, SubscriptionSettings
from app.features.notifications.notifier import format_notice
from app.features.notifications.schemas import is_level_enabled
from app.features.project_management.projects.errors import ProjectError
from app_layer_base.utils.time_util import get_current_utc_time


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def command_digest(data, target=None):
    return hashlib.sha256(
        json.dumps(
            {"target": str(target) if target else None, "body": data.model_dump(mode="json")}, sort_keys=True
        ).encode()
    ).hexdigest()


def matches(entry, sub):
    settings = SubscriptionSettings.model_validate(sub.settings)
    return (
        entry.actionable
        and entry.kind in settings.kinds
        and (settings.project_scope == "all" or entry.project_id in settings.project_ids)
    )


def subscription_read(channel, sub):
    return SubscriptionRead(
        channel_id=channel.id,
        revision=sub.revision if sub else 0,
        destination_generation=channel.destination_generation,
        settings=SubscriptionSettings.model_validate(sub.settings if sub else {}),
        channel_enabled=channel.enabled,
        severity_enabled=is_level_enabled(channel.min_level, "warning"),
        chat_id=(channel.config or {}).get("chat_id"),
        observed_at=get_current_utc_time(),
    )


class DecisionNoticeService:
    @staticmethod
    def require_channel(channel):
        if channel is None:
            raise ProjectError(404, "Notification channel not found")
        return channel

    @staticmethod
    def validate_basis(channel, sub, data):
        if (
            data.expected_revision != (sub.revision if sub else 0)
            or data.expected_destination_generation != channel.destination_generation
        ):
            raise ProjectError(409, "Decision notice settings or destination changed; review again")

    @staticmethod
    def enabled(channel, sub):
        return sub is not None and sub.enabled and channel.enabled and is_level_enabled(channel.min_level, "warning")

    @staticmethod
    def message(rows, origin):
        text = "Pending decisions (last observed evidence)"
        included = []
        for notice, entry, run, project in rows[:10]:
            link = (
                origin
                + "/decisions?"
                + urlencode({"decision_key": entry.key, "decision_fingerprint": entry.fingerprint})
            )
            age = "First observed" if entry.kind != "run-question" else "Waiting since"
            item = f"\n{entry.kind} | {project.name} | PR #{run.pull_number} | run {run.id}\n{age}: {entry.waiting_since.isoformat()} | Observed: {entry.observed_at.isoformat()}\n{link}"
            if len(format_notice(text + item, "warning")) > 3500:
                break
            text += item
            included.append(notice)
        return format_notice(text, "warning"), included

    @staticmethod
    def admit(session, channel, notices, message):
        now = get_current_utc_time()
        attempt = DecisionNoticeAttempt(
            id=uuid4(),
            channel_id=channel.id,
            destination_generation=channel.destination_generation,
            notice_ids=[str(n.id) for n in notices],
            message=message,
            state="sending",
            token=uuid4(),
            lease_expires_at=now + timedelta(seconds=60),
        )
        session.add(attempt)
        for n in notices:
            n.state, n.last_attempt_id = "sending", attempt.id
        return attempt
