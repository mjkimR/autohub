"""Cursor validation and discovery presentation; authentication follows run reads."""

import base64
import binascii
import json
from datetime import UTC, datetime

from app.features.project_management.pipeline_runs.discovery_schemas import DecisionEntryRead, DecisionPage
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError


def decode_cursor(cursor, filters):
    if cursor is None:
        return None
    try:
        if len(cursor) > 4096:
            raise ValueError
        data = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if set(data) != {"filters", "waiting", "key"} or data["filters"] != request_digest(filters):
            raise ValueError
        timestamp = datetime.fromisoformat(data["waiting"])
        if timestamp.tzinfo is None or not isinstance(data["key"], str):
            raise ValueError
        return timestamp, data["key"]
    except (ValueError, TypeError, KeyError, binascii.Error):
        raise ProjectError(422, "Invalid decision cursor or changed filters") from None


def page_result(rows, limit, filters):
    items = rows[:limit]
    more = len(rows) > limit
    cursor = None
    if more:
        row = items[-1]
        stamp = row.waiting_since.replace(tzinfo=UTC) if row.waiting_since.tzinfo is None else row.waiting_since
        cursor = base64.urlsafe_b64encode(
            json.dumps({"filters": request_digest(filters), "waiting": stamp.isoformat(), "key": row.key}).encode()
        ).decode()
    return DecisionPage(items=[DecisionEntryRead.model_validate(r) for r in items], has_more=more, next_cursor=cursor)
