import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases import advancement
from app.features.project_management.pipeline_runs.usecases.advancement import PipelineRunAdvancement
from app.features.project_management.pipeline_runs.usecases.delivery import CATALOG_HOLD_CODE
from app.features.project_management.projects.errors import ProjectError
from app_testing_base import hours_later

from tests.unit.features.project_management.pipeline_runs.usecases.test_lifecycle import create_mock_run

pytestmark = pytest.mark.unit


def state(name, **changes):
    value = PipelineRunRead.model_validate(create_mock_run(state=name))
    return value.model_copy(update=changes)


@pytest.fixture
def lifecycle():
    return MagicMock(
        acquire_lease=AsyncMock(return_value=MagicMock(token=uuid4())),
        release_lease=AsyncMock(),
        get=AsyncMock(),
        prepare_implementation=AsyncMock(),
        dispatch_implementation=AsyncMock(),
        observe_run=AsyncMock(),
    )


async def drive(lifecycle, **kwargs):
    return await PipelineRunAdvancement(lifecycle).advance_until_wait(uuid4(), MagicMock(), **kwargs)


async def test_push_ci_failure_and_repair_share_one_lease(lifecycle):
    lifecycle.get.return_value = state("implementing")
    lifecycle.observe_run.side_effect = [state("awaiting_ci"), state("dispatching")]
    delivered = state("implementing")
    lifecycle.dispatch_implementation.return_value = delivered
    assert await drive(lifecycle) is delivered
    assert lifecycle.observe_run.await_count == 2
    lifecycle.dispatch_implementation.assert_awaited_once()
    lifecycle.acquire_lease.assert_awaited_once()
    lifecycle.release_lease.assert_awaited_once()
    token = lifecycle.acquire_lease.return_value.token
    assert all(call.kwargs["token"] == token for call in lifecycle.observe_run.await_args_list)
    assert lifecycle.dispatch_implementation.await_args.kwargs["token"] == token
    assert lifecycle.release_lease.await_args.args[1].token == token


@pytest.mark.parametrize("name", ["implementing", "awaiting_ci"])
async def test_revision_only_changes_do_not_poll_again(lifecycle, name):
    initial = state(name)
    lifecycle.get.return_value = initial
    lifecycle.observe_run.return_value = initial.model_copy(update={"revision": initial.revision + 1})
    result = await drive(lifecycle)
    assert result.revision == initial.revision + 1
    lifecycle.observe_run.assert_awaited_once()
    lifecycle.dispatch_implementation.assert_not_awaited()


@pytest.mark.parametrize("name", ["paused", "blocked", "completed", "failed", "canceled"])
async def test_operator_and_terminal_states_stop(lifecycle, name):
    lifecycle.get.return_value = state(name)
    assert (await drive(lifecycle)).state == name
    lifecycle.observe_run.assert_not_awaited()
    lifecycle.dispatch_implementation.assert_not_awaited()


@pytest.mark.parametrize("name", ["queued", "dispatching", "implementing", "awaiting_ci"])
async def test_tick_respects_future_due_time(lifecycle, name):
    lifecycle.get.return_value = state(name, next_action_at=hours_later(1))
    await drive(lifecycle, respect_due=True)
    lifecycle.prepare_implementation.assert_not_awaited()
    lifecycle.observe_run.assert_not_awaited()
    lifecycle.dispatch_implementation.assert_not_awaited()


@pytest.mark.parametrize("name", ["queued", "dispatching", "awaiting_ci"])
async def test_event_refreshes_observation_but_cannot_bypass_delivery_delay(lifecycle, name):
    initial = state(name, next_action_at=hours_later(1))
    lifecycle.get.return_value = initial
    lifecycle.observe_run.return_value = initial
    await drive(lifecycle)
    assert lifecycle.observe_run.await_count == int(name == "awaiting_ci")
    lifecycle.dispatch_implementation.assert_not_awaited()
    lifecycle.prepare_implementation.assert_not_awaited()


async def test_new_retry_time_stops_continuation(lifecycle):
    lifecycle.get.return_value = state("implementing")
    lifecycle.observe_run.return_value = state("dispatching", next_action_at=hours_later(1))
    await drive(lifecycle)
    lifecycle.observe_run.assert_awaited_once()
    lifecycle.dispatch_implementation.assert_not_awaited()


async def test_catalog_hold_preserves_committed_observation(lifecycle):
    lifecycle.get.return_value = state("implementing")
    planned = state("dispatching")
    lifecycle.observe_run.return_value = planned
    lifecycle.dispatch_implementation.side_effect = ProjectError(409, "quota", code=CATALOG_HOLD_CODE)
    assert await drive(lifecycle) is planned
    lifecycle.dispatch_implementation.assert_awaited_once()
    lifecycle.release_lease.assert_awaited_once()


async def test_initial_catalog_hold_is_reported(lifecycle):
    lifecycle.get.return_value = state("dispatching")
    lifecycle.dispatch_implementation.side_effect = ProjectError(409, "quota", code=CATALOG_HOLD_CODE)
    with pytest.raises(ProjectError, match="quota"):
        await drive(lifecycle)
    lifecycle.release_lease.assert_awaited_once()


async def test_approval_and_integration_continue_without_another_tick(lifecycle):
    approval = {"approval": {"actor": "operator"}, "current": {"stage": {"id": "approval"}}}
    lifecycle.get.return_value = state("paused", sdd_progress={"waiting_for_approval": True})
    lifecycle.observe_run.side_effect = [
        state("implementing", sdd_progress=approval),
        state("awaiting_ci", sdd_progress={**approval, "integrated": True}),
        state("completed"),
    ]
    assert (await drive(lifecycle)).state == "completed"
    assert lifecycle.observe_run.await_count == 3


async def test_automatic_approval_continues_even_when_run_state_is_unchanged(lifecycle):
    lifecycle.get.return_value = state("implementing", sdd_progress={"current": {"stage": {"id": "approval"}}})
    lifecycle.observe_run.side_effect = [
        state("implementing", sdd_progress={"approval": {"actor": "policy"}}),
        state("awaiting_ci"),
        state("completed"),
    ]
    assert (await drive(lifecycle)).state == "completed"
    assert lifecycle.observe_run.await_count == 3


async def test_continuation_has_a_step_limit(lifecycle, monkeypatch):
    monkeypatch.setattr(advancement, "ADVANCE_MAX_STEPS", 3)
    lifecycle.get.return_value = state("implementing")
    lifecycle.observe_run.side_effect = [state("awaiting_ci"), state("implementing"), state("awaiting_ci")]
    assert (await drive(lifecycle)).state == "awaiting_ci"
    assert lifecycle.observe_run.await_count == 3
    lifecycle.release_lease.assert_awaited_once()


async def test_deadline_covers_all_steps_and_releases_lease(lifecycle, monkeypatch):
    monkeypatch.setattr(advancement, "ADVANCE_SECONDS", 0.01)
    lifecycle.get.return_value = state("implementing")
    calls = 0

    async def observe(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return state("awaiting_ci")
        await asyncio.Event().wait()

    lifecycle.observe_run.side_effect = observe
    with pytest.raises(ProjectError) as raised:
        await drive(lifecycle)
    assert raised.value.status_code == 504
    assert calls == 2
    lifecycle.release_lease.assert_awaited_once()


async def test_cancellation_releases_lease(lifecycle):
    lifecycle.get.return_value = state("implementing")
    lifecycle.observe_run.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await drive(lifecycle)
    lifecycle.release_lease.assert_awaited_once_with(ANY, ANY)
