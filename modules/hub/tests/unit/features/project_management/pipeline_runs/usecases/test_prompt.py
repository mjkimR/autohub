"""Committed mutations survive prompt refusal, partial progress and timeout."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.usecases import prompt
from app.features.project_management.projects.errors import ProjectError

pytestmark = pytest.mark.unit


async def test_success_uses_due_checks_and_returns_progress():
    run, progressed = MagicMock(id=uuid4()), MagicMock()
    lifecycle = MagicMock(advance_until_wait=AsyncMock(return_value=progressed))
    assert await prompt.advance_promptly(lifecycle, run) is progressed
    lifecycle.advance_until_wait.assert_awaited_once_with(run.id, lifecycle.observer, respect_due=True)


@pytest.mark.parametrize("unreadable", [False, True])
async def test_refusal_preserves_committed_result(unreadable):
    run, latest = MagicMock(id=uuid4()), MagicMock()
    lifecycle = MagicMock(
        advance_until_wait=AsyncMock(side_effect=ProjectError(409, "capacity")),
        get=AsyncMock(side_effect=RuntimeError() if unreadable else None, return_value=latest),
    )
    assert await prompt.advance_promptly(lifecycle, run) is (run if unreadable else latest)


async def test_timeout_leaves_partial_progress_for_tick(monkeypatch):
    run, latest = MagicMock(id=uuid4()), MagicMock()
    canceled = asyncio.Event()

    async def slow(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            canceled.set()

    lifecycle = MagicMock(advance_until_wait=slow, get=AsyncMock(return_value=latest))
    monkeypatch.setattr(prompt, "PROMPT_SECONDS", 0.001)
    assert await prompt.advance_promptly(lifecycle, run) is latest
    assert canceled.is_set()
