"""Owed-item kinds, cursor rules and presentation; no database or provider access."""

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import get_args
from uuid import UUID

from app.features.project_management.connection_tests.adapters.registry import ADAPTERS
from app.features.project_management.owed_items.schemas import (
    OwedItemCounts,
    OwedItemKind,
    OwedItemPage,
    OwedItemRead,
)
from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError

KINDS: tuple[str, ...] = get_args(OwedItemKind)
QUIET_KINDS = frozenset({"failed-run"})
# kind -> (subject type, action name, action label)
PRESENTATION = {
    "decision": ("decision", "answer", "Answer"),
    "stopped-run": ("pipeline-run", "resume-run", "Resume run"),
    "work-plan-proposed": ("work-plan", "review-plan", "Review plan"),
    "work-item-recovery": ("work-item-recovery", "inspect-recovery", "Inspect recovery"),
    "work-item-replacement": ("replacement-link", "accept-replacement", "Accept replacement"),
    "work-item-attention": ("work-item", "inspect-work-item", "Inspect Work Item"),
    "sdd-batch-attention": ("sdd-batch", "inspect-batch", "Inspect batch"),
    "connection-test-cleanup": ("connection-test", "review-cleanup", "Review cleanup"),
    "failed-run": ("pipeline-run", "inspect-run", "Inspect run"),
}
DECISION_CAUSES = {
    "run-question": "Run question awaits an answer",
    "native-hub-question": "SDD question awaits an answer",
    "native-worker-question": "SDD worker question awaits an answer",
    "native-workflow": "SDD workflow awaits a decision",
    "native-proposal": "SDD proposal awaits a decision",
    "native-integration": "SDD integration awaits approval",
}


def cleanup_adapters() -> list[tuple[str, str]]:
    """The connection-test adapter check, evaluated in code and applied to the SQL candidate filter."""
    return sorted(key for key, adapter in ADAPTERS.items() if adapter.spec.manual_cleanup_resolution)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _uuid(value) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    return UUID(str(value))


def decode_cursor(cursor: str | None, filters: dict) -> tuple[datetime, str] | None:
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
        raise ProjectError(422, "Invalid owed-item cursor or changed filters") from None


def _cursor(row, filters: dict) -> str:
    stamp = _utc(row["waiting_since"]).isoformat()
    payload = {"filters": request_digest(filters), "waiting": stamp, "key": row["sort_key"]}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _cause(row) -> str:
    kind, state, detail = row["kind"], row["state"], row["detail"]
    if kind == "decision":
        return DECISION_CAUSES.get(state, "Decision awaits the operator")
    if kind in ("stopped-run", "failed-run"):
        prefix = {"paused": "Run is paused", "blocked": "Run is blocked", "failed": "Run failed"}[state]
        return f"{prefix}: {detail}" if detail else prefix
    if kind == "work-plan-proposed":
        return "Work Plan is proposed and needs a decision"
    if kind == "work-item-recovery":
        return f"Recovery is {state}: {detail}" if detail else f"Recovery is {state}"
    if kind == "work-item-replacement":
        return "Replacement has a dependent edge awaiting acceptance"
    if kind == "work-item-attention":
        return f"Work Item needs attention: {detail}" if detail else "Work Item needs attention"
    if kind == "sdd-batch-attention":
        return f"SDD batch needs attention: {detail}" if detail else "SDD batch needs attention"
    return "Connection-test cleanup needs review"


def present(row) -> OwedItemRead:
    kind = row["kind"]
    subject_type, action, label = PRESENTATION[kind]
    # SQLite renders UUID text without hyphens; the public key always uses the canonical form.
    subject_id = row["subject_id"] if kind == "decision" else str(UUID(row["subject_id"]))
    hold = None
    if row["catalog_hold"]:
        hold = {
            "catalog_id": _uuid(row["catalog_id"]),
            "reason": row["catalog_hold"],
            "available_at": _utc(row["catalog_available_at"]) if row["catalog_available_at"] else None,
        }
    return OwedItemRead.model_validate(
        {
            "key": f"{kind}:{subject_id}",
            "kind": kind,
            "counted": kind not in QUIET_KINDS,
            "cause": _cause(row),
            "subject": {
                "type": subject_type,
                "id": subject_id,
                "project_id": _uuid(row["project_id"]),
                "title": row["title"],
            },
            "primary_action": {"name": action, "label": label},
            "waiting_since": _utc(row["waiting_since"]),
            "context": {
                "run_id": _uuid(row["run_id"]),
                "work_plan_id": _uuid(row["work_plan_id"]),
                "work_item_id": _uuid(row["work_item_id"]),
                "sdd_batch_id": _uuid(row["sdd_batch_id"]),
                "catalog_hold": hold,
            },
        }
    )


def page_result(rows, limit: int, filters: dict) -> OwedItemPage:
    items = rows[:limit]
    more = len(rows) > limit
    return OwedItemPage(
        items=[present(row) for row in items],
        has_more=more,
        next_cursor=_cursor(items[-1], filters) if more else None,
    )


def counts_result(groups) -> OwedItemCounts:
    by_kind = dict.fromkeys(KINDS, 0)
    by_project: dict[str, int] = {}
    for kind, project_id, count in groups:
        by_kind[kind] += count
        if kind not in QUIET_KINDS:
            project = str(_uuid(project_id))
            by_project[project] = by_project.get(project, 0) + count
    total = sum(count for kind, count in by_kind.items() if kind not in QUIET_KINDS)
    return OwedItemCounts.model_validate({"total": total, "by_kind": by_kind, "by_project": by_project})
