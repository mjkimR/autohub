from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.features.execution.tasks.core.context import task_context
from app.features.execution.tasks.domains.pipeline.task import dispatch_project_task
from app.features.project_management.pipeline_runs.models import PipelineRun, PipelineRunState
from app.features.project_management.pipeline_runs.schemas import LeaseGrant
from app.features.project_management.pipeline_runs.usecases.lifecycle import CATALOG_HOLD_CODE
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.schemas import ProjectDispatchPayload

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_credential_provider(monkeypatch, credential_key_provider):
    monkeypatch.setattr(
        "app.features.execution.tasks.domains.pipeline.task.get_credential_key_provider",
        lambda: credential_key_provider,
    )


@pytest.fixture(autouse=True)
def project_run_limit(monkeypatch):
    """The project's `max_in_flight_runs`; these tests have no project row to read it from."""
    limit = AsyncMock(return_value=None)
    monkeypatch.setattr("app.features.execution.tasks.domains.pipeline.task._project_run_limit", limit)
    return limit


async def test_dispatch_task_fails_outside_task_context():
    payload = ProjectDispatchPayload(project_id=uuid4())
    with pytest.raises(RuntimeError, match="requires a schedule task context"):
        await dispatch_project_task(payload)


async def test_dispatch_task_noops_when_no_active_run():
    project_id = uuid4()
    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_active = AsyncMock(return_value=[])

        await dispatch_project_task(ProjectDispatchPayload(project_id=project_id))

        assert mock_repo.list_active.await_count == 2


async def test_dispatch_task_acquires_lease_and_prepares_implementation_for_queued_run():
    project_id = uuid4()
    run_id = uuid4()
    lease_token = uuid4()

    mock_run = MagicMock(spec=PipelineRun)
    mock_run.id = run_id
    mock_run.state = PipelineRunState.QUEUED
    mock_run.next_action_at = None

    grant = MagicMock(spec=LeaseGrant)
    grant.token = lease_token
    grant.run_revision = 1

    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_active = AsyncMock(side_effect=[[], [mock_run]])

        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=grant)
        mock_use_case.prepare_implementation = AsyncMock()
        mock_use_case.release_lease = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=project_id))

        assert mock_repo.list_active.await_count == 2
        mock_use_case.acquire_lease.assert_awaited_once()
        mock_use_case.prepare_implementation.assert_awaited_once()
        mock_use_case.release_lease.assert_awaited_once()


async def test_dispatch_task_acquires_lease_and_delivers_a_prepared_implementation():
    project_id = uuid4()
    run_id = uuid4()
    lease_token = uuid4()

    mock_run = MagicMock(spec=PipelineRun)
    mock_run.id = run_id
    mock_run.state = PipelineRunState.DISPATCHING
    mock_run.next_action_at = None

    grant = MagicMock(spec=LeaseGrant)
    grant.token = lease_token
    grant.run_revision = 2

    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_active = AsyncMock(side_effect=[[], [mock_run]])

        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=grant)
        mock_use_case.dispatch_implementation = AsyncMock(return_value=mock_run)
        mock_use_case.release_lease = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=project_id))

        assert mock_repo.list_active.await_count == 2
        mock_use_case.acquire_lease.assert_awaited_once()
        mock_use_case.dispatch_implementation.assert_awaited_once_with(run_id, owner=ANY, token=lease_token)
        mock_use_case.release_lease.assert_awaited_once()


async def test_dispatch_task_prepares_multiple_pull_requests_in_parallel_batch():
    project_id = uuid4()
    runs = []
    for _ in range(2):
        run = MagicMock(spec=PipelineRun)
        run.id = uuid4()
        run.state = PipelineRunState.QUEUED
        run.next_action_at = None
        runs.append(run)
    grant = MagicMock(spec=LeaseGrant)
    grant.token = uuid4()
    grant.run_revision = 1

    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_active = AsyncMock(side_effect=[[], runs])
        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=grant)
        mock_use_case.prepare_implementation = AsyncMock()
        mock_use_case.release_lease = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=project_id))

    assert mock_use_case.acquire_lease.await_count == 2
    assert mock_use_case.prepare_implementation.await_count == 2
    assert mock_use_case.release_lease.await_count == 2


async def test_dispatch_task_recovers_a_run_when_its_webhook_was_missed():
    """Scheduler polling advances a ready run even without a webhook delivery."""
    project_id = uuid4()
    run_id = uuid4()
    token = uuid4()
    run = MagicMock(spec=PipelineRun)
    run.id = run_id
    run.state = PipelineRunState.IMPLEMENTING
    run.next_action_at = None
    grant = MagicMock(spec=LeaseGrant)
    grant.token = token

    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo_cls.return_value.list_active = AsyncMock(side_effect=[[run], []])
        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=grant)
        mock_use_case.advance_run = AsyncMock(return_value=run)
        mock_use_case.release_lease = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=project_id))

    mock_use_case.advance_run.assert_awaited_once_with(run_id, owner=ANY, token=token, observer=ANY)
    mock_use_case.release_lease.assert_awaited_once()


@pytest.mark.parametrize("observation_fails", [False, True])
async def test_observers_finish_before_dispatch_even_when_one_fails(observation_fails):
    import asyncio

    runs = []
    for state in (PipelineRunState.DISPATCHING, PipelineRunState.IMPLEMENTING, PipelineRunState.AWAITING_CI):
        run = MagicMock(spec=PipelineRun)
        run.id, run.state = uuid4(), state
        runs.append(run)
    released = set()
    grant = MagicMock(spec=LeaseGrant)
    grant.token = uuid4()

    async def observe(run_id, **kwargs):
        if observation_fails and run_id == runs[1].id:
            raise RuntimeError("observation failed")
        await asyncio.sleep(0)

    async def release(run_id, request):
        released.add(run_id)

    async def dispatch(*args, **kwargs):
        assert {run.id for run in runs[1:]} <= released

    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as repo,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as usecase,
    ):

        async def select_batch(session, project_id, *, states, **kwargs):
            if PipelineRunState.IMPLEMENTING in states:
                return runs[1:]
            assert {run.id for run in runs[1:]} <= released
            return runs[:1]

        repo.return_value.list_active = AsyncMock(side_effect=select_batch)
        lifecycle = usecase.return_value
        lifecycle.acquire_lease = AsyncMock(return_value=grant)
        lifecycle.advance_run = AsyncMock(side_effect=observe)
        lifecycle.dispatch_implementation = AsyncMock(side_effect=dispatch)
        lifecycle.release_lease = AsyncMock(side_effect=release)
        if observation_fails:
            with pytest.raises(RuntimeError, match="observation failed"):
                await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))
        else:
            await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))
        lifecycle.dispatch_implementation.assert_awaited_once()
        assert released == {run.id for run in runs}


def queued_run() -> MagicMock:
    run = MagicMock(spec=PipelineRun)
    run.id = uuid4()
    run.state = PipelineRunState.QUEUED
    run.next_action_at = None
    run.pause_reason = None
    return run


def lease_grant() -> MagicMock:
    grant = MagicMock(spec=LeaseGrant)
    grant.token = uuid4()
    grant.run_revision = 1
    return grant


async def test_queued_runs_wait_while_the_project_has_its_limit_of_started_runs(project_run_limit):
    project_run_limit.return_value = 2
    runs = [queued_run(), queued_run(), queued_run()]
    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.list_active = AsyncMock(side_effect=[[], runs])
        mock_repo.count_started = AsyncMock(return_value=1)
        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=lease_grant())
        mock_use_case.prepare_implementation = AsyncMock()
        mock_use_case.release_lease = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))

        # One slot is free, and the oldest queued run takes it.
        mock_use_case.prepare_implementation.assert_awaited_once_with(runs[0].id, ANY)


@pytest.mark.parametrize(
    ("failure", "waits_with"),
    [
        (
            GitHubObservationError("GitHub observation returned HTTP 403", 403, kind="rate_limited", retry_after=120),
            {"kind": "rate_limited", "retry_after": 120},
        ),
        (
            GitHubObservationError("GitHub observation returned HTTP 401", 401, kind="auth"),
            {"kind": "auth", "retry_after": None},
        ),
        (
            ProjectError(502, "GitHub merge returned HTTP 401", code="GITHUB_AUTH"),
            {"kind": "auth", "retry_after": None},
        ),
    ],
)
async def test_a_run_github_will_not_serve_waits_instead_of_failing_the_tick(failure, waits_with):
    run = queued_run()
    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo_cls.return_value.list_active = AsyncMock(side_effect=[[], [run]])
        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=lease_grant())
        mock_use_case.prepare_implementation = AsyncMock(side_effect=failure)
        mock_use_case.release_lease = AsyncMock()
        mock_use_case.wait_for_github = AsyncMock()

        await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))

        mock_use_case.wait_for_github.assert_awaited_once_with(run.id, **waits_with)
        mock_use_case.release_lease.assert_awaited_once()


async def test_a_catalog_hold_is_backpressure_but_other_errors_still_fail_the_tick():
    held, broken = queued_run(), queued_run()
    with (
        task_context(config_id=uuid4(), config_name="test", run_id=uuid4()),
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunRepository") as mock_repo_cls,
        patch("app.features.execution.tasks.domains.pipeline.task.PipelineRunUseCase") as mock_use_case_cls,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_use_case = mock_use_case_cls.return_value
        mock_use_case.acquire_lease = AsyncMock(return_value=lease_grant())
        mock_use_case.release_lease = AsyncMock()
        mock_use_case.wait_for_github = AsyncMock()

        mock_repo.list_active = AsyncMock(side_effect=[[], [held]])
        mock_use_case.prepare_implementation = AsyncMock(
            side_effect=ProjectError(409, "AI catalog is quota-blocked", code=CATALOG_HOLD_CODE)
        )
        await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))

        mock_repo.list_active = AsyncMock(side_effect=[[], [broken]])
        mock_use_case.prepare_implementation = AsyncMock(side_effect=ProjectError(502, "GitHub returned HTTP 500"))
        with pytest.raises(ProjectError):
            await dispatch_project_task(ProjectDispatchPayload(project_id=uuid4()))
        mock_use_case.wait_for_github.assert_not_awaited()
