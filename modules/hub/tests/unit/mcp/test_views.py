from datetime import timedelta
from uuid import uuid4

import pytest
from app.features.project_management.connection_tests.adapters.specs import CODEX_SPEC
from app.features.project_management.connection_tests.schemas import (
    ConnectionTestOption,
    ConnectionTestRead,
    RequirementStatus,
)
from app.mcp import waiting
from app.mcp.contracts import ReadinessView
from app.mcp.contracts import TestView as ConnectionTestView
from app.mcp.waiting import wait_for_change
from app_testing_base import utc_now

pytestmark = pytest.mark.unit


def make_test(evidence: dict, **overrides) -> ConnectionTestRead:
    now = utc_now()
    return ConnectionTestRead.model_validate(
        {
            "id": uuid4(),
            "project_id": uuid4(),
            "project_revision": 1,
            "repository": "owner/app",
            "ai_catalog_id": None,
            "catalog_snapshot": None,
            "test_spec": CODEX_SPEC,
            "status": "running",
            "phase": "waiting_for_push",
            "cleanup_status": "pending",
            "detail": None,
            "evidence": evidence,
            "cancel_requested": False,
            "created_at": now,
            "deadline": now + timedelta(hours=1),
            "finished_at": None,
        }
        | overrides
    )


class TestConnectionTestView:
    def test_exposes_only_public_evidence_from_trusted_origins(self):
        view = ConnectionTestView.from_read(
            make_test(
                {
                    "pull_url": "https://github.com/owner/app/pull/30",
                    "comment_url": "https://evil.example/owner/app/pull/30",
                    "reply_url": "https://user:pass@github.com/owner/app/pull/30",
                    "ci_status": "success",
                    "owned_pulls": {"30": {"proof": "created"}},
                    "cleanup_error": "Branch deletion failed",
                }
            )
        )
        assert view.evidence == {
            "pull_url": "https://github.com/owner/app/pull/30",
            "ci_status": "success",
            "cleanup_error": "Branch deletion failed",
        }
        assert view.phase_label == CODEX_SPEC.phases["waiting_for_push"]

    @pytest.mark.parametrize(
        ("status", "cleanup", "settled"),
        [("running", "pending", False), ("succeeded", "pending", False), ("succeeded", "completed", True)],
    )
    def test_settles_only_after_cleanup_finishes(self, status, cleanup, settled):
        assert ConnectionTestView.from_read(make_test({}, status=status, cleanup_status=cleanup)).settled is settled


def test_readiness_lists_only_unconfigured_requirements():
    option = ConnectionTestOption(
        ai_catalog_id=uuid4(),
        name="Personal Codex",
        kind="codex",
        spec=CODEX_SPEC,
        requirements=[
            RequirementStatus(key="github", status="configured"),
            RequirementStatus(key="codex_account", status="manual"),
        ],
        configuration_fingerprint="fingerprint",
        ready=True,
    )
    view = ReadinessView.from_option(option)
    assert [item.key for item in view.pending] == ["codex_account"]
    assert view.pending[0].url == "https://chatgpt.com/codex"
    assert view.test_title == CODEX_SPEC.title


class TestWaitForChange:
    @pytest.fixture(autouse=True)
    def fast_polls(self, monkeypatch):
        monkeypatch.setattr(waiting, "POLL_INTERVAL_SECONDS", 0.01)

    async def test_returns_immediately_without_waiting(self):
        reads = iter([1, 2])
        assert await wait_for_change(lambda: _value(next(reads)), lambda v: v, lambda v: False, 0) == 1

    async def test_returns_the_first_changed_value(self):
        reads = iter([1, 1, 2, 3])
        assert await wait_for_change(lambda: _value(next(reads)), lambda v: v, lambda v: False, 5) == 2

    async def test_settled_values_return_without_polling(self):
        reads = iter([1])
        assert await wait_for_change(lambda: _value(next(reads)), lambda v: v, lambda v: True, 5) == 1

    async def test_gives_up_after_the_deadline(self):
        assert await wait_for_change(lambda: _value(1), lambda v: v, lambda v: False, 1) == 1


async def _value[T](value: T) -> T:
    return value
