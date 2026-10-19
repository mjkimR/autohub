from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.features.execution.tasks.core.context import task_context
from app.features.execution.tasks.domains.pipeline import task as task_module
from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.usecases.delivery import CATALOG_HOLD_CODE
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.schemas import ProjectDispatchPayload

pytestmark = pytest.mark.unit


def run(state: str = PipelineRunState.QUEUED):
    return SimpleNamespace(id=uuid4(), state=state, next_action_at=None, pause_reason=None)


@pytest.fixture
def worker(monkeypatch, credential_key_provider):
    monkeypatch.setattr(task_module, "get_credential_key_provider", lambda: credential_key_provider)
    monkeypatch.setattr(task_module, "get_scheduler_defaults", lambda: SimpleNamespace(MAX_CONCURRENT_TASKS=2))
    repo = MagicMock(list_active=AsyncMock(return_value=[]), count_started=AsyncMock(return_value=0))
    lifecycle = MagicMock(
        advance_until_wait=AsyncMock(return_value=run("implementing")),
        wait_for_github=AsyncMock(),
        clear_github_auth_wait=AsyncMock(),
    )
    limit, work = AsyncMock(return_value=None), AsyncMock()
    monkeypatch.setattr(task_module, "PipelineRunRepository", lambda: repo)
    monkeypatch.setattr(task_module, "PipelineRunUseCase", lambda *args: lifecycle)
    monkeypatch.setattr(task_module, "_project_run_limit", limit)
    monkeypatch.setattr(task_module.WorkPlanExecution, "advance_project", work)
    return SimpleNamespace(repo=repo, lifecycle=lifecycle, limit=limit, work=work)


async def tick():
    with task_context(config_id=uuid4(), config_name="test", run_id=uuid4()):
        await task_module.dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))


async def test_dispatch_task_fails_outside_task_context(worker):
    with pytest.raises(RuntimeError, match="requires a schedule task context"):
        await task_module.dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))


async def test_empty_tick_still_reconciles_work(worker):
    await tick()
    worker.work.assert_awaited_once()
    worker.lifecycle.advance_until_wait.assert_not_awaited()


@pytest.mark.parametrize("state", ["queued", "dispatching", "implementing", "awaiting_ci", "paused"])
async def test_every_selected_state_uses_the_common_advancer(worker, state):
    item = run(state)
    observations = state in ("implementing", "awaiting_ci", "paused")
    worker.repo.list_active.side_effect = [[item] if observations else [], [] if observations else [item], []]
    await tick()
    worker.lifecycle.advance_until_wait.assert_awaited_once_with(item.id, ANY, owner=ANY, respect_due=True)
    assert worker.lifecycle.advance_until_wait.await_args.kwargs["owner"].startswith("job:")


async def test_observation_failure_does_not_starve_dispatch(worker):
    observing, queued = run("implementing"), run()
    worker.repo.list_active.side_effect = [[observing], [queued], []]

    async def advance(run_id, *args, **kwargs):
        if run_id == observing.id:
            raise RuntimeError("observation failed")
        return run("implementing")

    worker.lifecycle.advance_until_wait.side_effect = advance
    with pytest.raises(RuntimeError, match="observation failed"):
        await tick()
    assert [c.args[0] for c in worker.lifecycle.advance_until_wait.await_args_list] == [observing.id, queued.id]
    worker.work.assert_awaited_once()


async def test_project_capacity_limits_new_runs(worker):
    queued = [run(), run()]
    worker.limit.return_value = 2
    worker.repo.count_started.return_value = 1
    worker.repo.list_active.side_effect = [[], queued, []]
    await tick()
    worker.lifecycle.advance_until_wait.assert_awaited_once_with(queued[0].id, ANY, owner=ANY, respect_due=True)


async def test_work_follow_up_uses_remaining_budget_after_existing_runs(worker):
    existing, ready, overflow = run(), run(), run()
    worker.repo.list_active.side_effect = [[], [existing], [ready, overflow]]

    async def prepare_work(*args, **kwargs):
        worker.lifecycle.advance_until_wait.assert_awaited_once_with(existing.id, ANY, owner=ANY, respect_due=True)

    worker.work.side_effect = prepare_work
    await tick()
    assert [c.args[0] for c in worker.lifecycle.advance_until_wait.await_args_list] == [existing.id, ready.id]


async def test_full_dispatch_batch_does_not_expand_for_follow_up(worker):
    worker.repo.list_active.side_effect = [[], [run(), run()]]
    await tick()
    assert worker.lifecycle.advance_until_wait.await_count == 2
    assert worker.repo.list_active.await_count == 2
    worker.work.assert_awaited_once()


async def test_observed_run_is_excluded_from_later_dispatch_selection(worker):
    observed, queued = run("implementing"), run()
    worker.repo.list_active.side_effect = [[observed], [queued], []]
    await tick()
    assert worker.repo.list_active.await_args_list[1].kwargs["exclude_ids"] == (observed.id,)
    assert set(worker.repo.list_active.await_args_list[2].kwargs["exclude_ids"]) == {observed.id, queued.id}


async def test_pending_dispatch_is_reconsidered_once_within_the_dispatch_budget(worker):
    observed, queued, overflow = run("awaiting_ci"), run(), run()
    pending = run("dispatching")
    pending.id = observed.id
    worker.repo.list_active.side_effect = [[observed], [pending, queued, overflow]]
    worker.lifecycle.advance_until_wait.side_effect = [
        pending,
        ProjectError(409, "capacity still full", code=CATALOG_HOLD_CODE),
        run("implementing"),
    ]
    await tick()
    assert worker.repo.list_active.await_args_list[1].kwargs["exclude_ids"] == ()
    assert [c.args[0] for c in worker.lifecycle.advance_until_wait.await_args_list] == [
        observed.id,
        observed.id,
        queued.id,
    ]
    assert worker.repo.list_active.await_count == 2


async def test_uncertain_delivery_after_observation_is_not_retried(worker):
    observed = run("awaiting_ci")
    worker.repo.list_active.side_effect = [[observed], [], []]
    worker.lifecycle.advance_until_wait.side_effect = ProjectError(504, "Delivery timed out")
    with pytest.raises(ProjectError, match="Delivery timed out"):
        await tick()
    worker.lifecycle.advance_until_wait.assert_awaited_once()
    assert all(observed.id in call.kwargs["exclude_ids"] for call in worker.repo.list_active.await_args_list[1:])


@pytest.mark.parametrize(
    ("failure", "waits_with"),
    [
        (
            GitHubObservationError("rate limit", 403, kind="rate_limited", retry_after=120),
            {"kind": "rate_limited", "retry_after": 120},
        ),
        (GitHubObservationError("auth", 401, kind="auth"), {"kind": "auth", "retry_after": None}),
        (ProjectError(502, "auth", code="GITHUB_AUTH"), {"kind": "auth", "retry_after": None}),
    ],
)
async def test_github_backpressure_is_recorded_without_failing_tick(worker, failure, waits_with):
    item = run()
    worker.repo.list_active.side_effect = [[], [item], []]
    worker.lifecycle.advance_until_wait.side_effect = failure
    await tick()
    worker.lifecycle.wait_for_github.assert_awaited_once_with(item.id, **waits_with)


async def test_catalog_hold_is_not_retried_in_the_same_tick(worker):
    item = run()
    worker.repo.list_active.side_effect = [[], [item], [item]]
    worker.lifecycle.advance_until_wait.side_effect = ProjectError(409, "quota", code=CATALOG_HOLD_CODE)
    await tick()
    worker.lifecycle.advance_until_wait.assert_awaited_once()
    worker.lifecycle.wait_for_github.assert_not_awaited()


async def test_success_clears_previous_auth_wait(worker):
    item = run("implementing")
    item.pause_reason = task_module.GITHUB_AUTH_WAIT_REASON
    worker.repo.list_active.side_effect = [[item], [], []]
    await tick()
    worker.lifecycle.clear_github_auth_wait.assert_awaited_once_with(item.id)
