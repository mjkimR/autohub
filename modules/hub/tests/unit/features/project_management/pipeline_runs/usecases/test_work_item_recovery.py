from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.adapters.base import DeliveryTarget
from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter
from app.features.project_management.pipeline_runs.usecases.implementation import (
    ImplementationInput,
    ImplementationObservation,
    ImplementationProgress,
)

from tests.unit.features.project_management.pipeline_runs.usecases.test_lifecycle import create_mock_run

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("cause,expected", [("initial", "dispatching"), ("recovery", "blocked")])
async def test_review_ordinary_ci_fix_keeps_its_silent_allowance_but_recovery_does_not(cause, expected):
    now = datetime(2026, 11, 5, tzinfo=UTC)
    run = create_mock_run()
    earlier = SimpleNamespace(id=uuid4(), epoch=run.epoch)
    current = SimpleNamespace(id=uuid4(), epoch=run.epoch)
    delivery = SimpleNamespace(cause=cause, delivery_number=1, posted_at=now - timedelta(hours=3))
    repo = MagicMock()
    repo.active_attempt = AsyncMock(return_value=current)
    repo.latest_delivery = AsyncMock(return_value=delivery)
    repo.list_attempts = AsyncMock(return_value=[earlier, current])
    repo.list_deliveries = AsyncMock(
        side_effect=lambda session, attempt_id: (
            [SimpleNamespace(cause="silent")] if attempt_id == earlier.id else [delivery]
        )
    )
    repo.create_delivery = AsyncMock()
    prepared = ImplementationInput(
        DeliveryTarget(uuid4(), "owner/repo", 10), delivery.posted_at, "a" * 40, CodexGithubMentionAdapter()
    )
    observed = ImplementationObservation({"state": "open", "head": {"sha": "a" * 40}}, [])
    result = await ImplementationProgress(repo, None).apply(AsyncMock(), run, now, prepared, observed)
    assert result.state == expected
    if expected == "dispatching":
        repo.create_delivery.assert_awaited_once()
    else:
        repo.create_delivery.assert_not_awaited()
