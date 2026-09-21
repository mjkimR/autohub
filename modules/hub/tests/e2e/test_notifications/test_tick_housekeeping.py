from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.features.ai_catalogs.models import AICatalog, AICatalogKind, AICatalogState
from app.features.configuration.system_configs.models import SystemConfig
from app.features.execution.dispatchers.usecases.housekeeping import HEARTBEAT_CONFIG
from app.features.project_management.github_webhooks.models import GitHubWebhookDelivery
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import (
    GITHUB_AUTH_WAIT_REASON,
    PipelineRunUseCase,
)
from app.features.project_management.projects.models import Project
from app.features.scheduling.schedule_configs.models import ScheduleConfig  # noqa: F401
from app.features.scheduling.schedule_jobs.models import ScheduleJob  # noqa: F401
from app_testing_base import utc_now
from sqlalchemy import select

from tests.utils.assertions import assert_status_code

pytestmark = pytest.mark.e2e

TRIGGER = "/api/v1/dispatchers/trigger"


async def make_run(session, *, state: str, pause_reason: str | None = None) -> PipelineRun:
    catalog = AICatalog(
        key=f"codex-{uuid4().hex[:8]}",
        name="Codex",
        kind=AICatalogKind.CODEX,
        adapter="codex-github-mention",
        enabled=True,
        availability_state=AICatalogState.NORMAL,
        revision=1,
    )
    project = Project(name="Application", github_repository=f"owner/app-{uuid4().hex[:6]}", automation={})
    session.add_all([catalog, project])
    await session.flush()
    run = PipelineRun(
        project_id=project.id,
        ai_catalog_id=catalog.id,
        project_revision=1,
        github_repository=project.github_repository,
        pull_number=42,
        pull_url=f"https://github.com/{project.github_repository}/pull/42",
        pull_snapshot={},
        state=state,
        pause_reason=pause_reason,
        branch="feature",
        revision=3,
    )
    session.add(run)
    await session.commit()
    return run


async def test_a_stopped_run_is_announced_once_and_again_when_it_stops_anew(client, session, channel, telegram):
    run = await make_run(session, state=PipelineRunState.BLOCKED, pause_reason="CI failed twice; resume manually")
    await make_run(session, state=PipelineRunState.AWAITING_CI)

    assert_status_code(await client.post(TRIGGER), 200)
    assert_status_code(await client.post(TRIGGER), 200)

    [text] = telegram.texts
    assert text == (
        f"Auto Hub: run blocked - {run.github_repository}#42\n{run.pull_url}\nReason: CI failed twice; resume manually"
    )

    await session.refresh(run)
    run.state, run.pause_reason, run.revision = PipelineRunState.PAUSED, "Merge failed", run.revision + 1
    await session.commit()
    assert_status_code(await client.post(TRIGGER), 200)

    assert len(telegram.texts) == 2 and "run paused" in telegram.texts[1]


async def test_a_stop_nobody_could_be_told_about_waits_for_a_working_channel(client, session, channel, telegram):
    run = await make_run(session, state=PipelineRunState.PAUSED, pause_reason="Merge failed")
    telegram.response = (403, {"ok": False, "description": "Forbidden: bot was blocked by the user"})

    assert_status_code(await client.post(TRIGGER), 200)
    await session.refresh(run)
    assert run.notified_revision is None

    telegram.response = (200, {"ok": True})
    assert_status_code(await client.post(TRIGGER), 200)
    await session.refresh(run)
    assert run.notified_revision == run.revision
    assert len(telegram.requests) == 2


async def test_without_a_channel_a_tick_still_succeeds(client, session, telegram):
    await make_run(session, state=PipelineRunState.FAILED)

    assert_status_code(await client.post(TRIGGER), 200)

    assert telegram.requests == []


async def test_health_reports_the_trigger_and_a_resumed_trigger_is_announced(client, session, channel, telegram):
    assert (await client.get("/api/health/deep")).json()["scheduler"] == "never"

    assert_status_code(await client.post(TRIGGER), 200)
    health = (await client.get("/api/health/deep")).json()
    assert (health["scheduler"], health["database"]) == ("ok", "connected")
    assert health["last_tick_at"] is not None and telegram.texts == []

    heartbeat = await session.scalar(select(SystemConfig).where(SystemConfig.name == HEARTBEAT_CONFIG))
    heartbeat.data = {"last_tick_at": (utc_now() - timedelta(minutes=45)).isoformat()}
    await session.commit()
    assert (await client.get("/api/health/deep")).json()["scheduler"] == "stale"

    assert_status_code(await client.post(TRIGGER), 200)

    [text] = telegram.texts
    assert "fired again after 45 minutes of silence" in text
    assert (await client.get("/api/health/deep")).json()["scheduler"] == "ok"


async def test_a_lost_auto_run_delivery_is_replayed_by_the_next_tick(client, session, channel, telegram):
    session.add_all(
        [
            GitHubWebhookDelivery(
                delivery_id="lost-trigger",
                event="issue_comment",
                repository="owner/unknown",
                payload_digest="0" * 64,
                pull_number=7,
                auto_run=True,
                created_at=utc_now() - timedelta(minutes=5),
            ),
            GitHubWebhookDelivery(
                delivery_id="still-in-flight",
                event="issue_comment",
                repository="owner/unknown",
                payload_digest="1" * 64,
                pull_number=8,
                auto_run=True,
            ),
        ]
    )
    await session.commit()

    assert_status_code(await client.post(TRIGGER), 200)

    rows = {
        row.delivery_id: row
        for row in (await session.scalars(select(GitHubWebhookDelivery).execution_options(populate_existing=True)))
    }
    # No project owns the repository, so the replay completes without enrolling anything.
    assert (rows["lost-trigger"].status, rows["lost-trigger"].attempts) == ("processed", 1)
    assert (rows["still-in-flight"].status, rows["still-in-flight"].attempts) == ("received", 0)
    assert telegram.texts == []


async def test_a_run_waiting_on_rejected_credentials_is_announced_once_and_recovers(client, session, channel, telegram):
    run = await make_run(session, state=PipelineRunState.AWAITING_CI)
    lifecycle = PipelineRunUseCase(PipelineRunRepository(), MagicMock(), MagicMock())

    await lifecycle.wait_for_github(run.id, kind="auth", retry_after=None)
    await lifecycle.wait_for_github(run.id, kind="auth", retry_after=None)
    assert_status_code(await client.post(TRIGGER), 200)
    assert_status_code(await client.post(TRIGGER), 200)

    [text] = telegram.texts
    assert text.startswith(f"Auto Hub: run waiting - {run.github_repository}#42")
    assert "connector token was rejected" in text
    await session.refresh(run)
    assert (run.state, run.pause_reason) == (PipelineRunState.AWAITING_CI, GITHUB_AUTH_WAIT_REASON)
    assert run.next_action_at is not None

    await lifecycle.clear_github_auth_wait(run.id)
    await session.refresh(run)
    assert run.pause_reason is None


async def test_a_rate_limit_only_delays_the_run(client, session, channel, telegram):
    run = await make_run(session, state=PipelineRunState.IMPLEMENTING)
    lifecycle = PipelineRunUseCase(PipelineRunRepository(), MagicMock(), MagicMock())

    await lifecycle.wait_for_github(run.id, kind="rate_limited", retry_after=600)
    assert_status_code(await client.post(TRIGGER), 200)

    await session.refresh(run)
    assert run.pause_reason is None and run.revision == 3
    assert run.next_action_at is not None and run.next_action_at.replace(tzinfo=None) > utc_now().replace(
        tzinfo=None
    ) + timedelta(minutes=9)
    assert telegram.texts == []
