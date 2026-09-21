import asyncio

from app.common.config import get_scheduler_defaults
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.execution.tasks import task
from app.features.execution.tasks.core.context import get_task_meta
from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import (
    LeaseMutation,
    LeaseRequest,
    PrepareImplementationAttempt,
)
from app.features.project_management.pipeline_runs.usecases.lifecycle import (
    CATALOG_HOLD_CODE,
    GITHUB_AUTH_WAIT_REASON,
    PipelineRunUseCase,
)
from app.features.project_management.pipelines.github import (
    GITHUB_FAILURE_AUTH,
    GITHUB_FAILURE_RATE_LIMITED,
    GitHubObservationError,
)
from app.features.project_management.pipelines.repos import PipelineObservationRepository
from app.features.project_management.pipelines.schemas import PipelineObservationConfig
from app.features.project_management.pipelines.services import OBSERVATION_TASK, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import (
    PROJECT_DISPATCH_TASK,
    PROJECT_OBSERVATION_TASK,
    ProjectRepository,
)
from app.features.project_management.projects.schemas import (
    ProjectDispatchPayload,
    ProjectObservationPayload,
    ProjectRead,
)
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time

WAITABLE_GITHUB_FAILURES = (GITHUB_FAILURE_AUTH, GITHUB_FAILURE_RATE_LIMITED)


@task(name=OBSERVATION_TASK)
async def observe_pipeline_task(payload: PipelineObservationConfig) -> None:
    """Observe required GitHub Actions jobs for configured PRs and save the latest report. No external writes."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError("pipeline.observe requires a schedule task context")
    service = PipelineObservationService(
        PipelineObservationRepository(), ConnectorCredentialCipher(get_credential_key_provider())
    )
    await service.observe_and_save(payload, meta.config_id)


@task(name=PROJECT_OBSERVATION_TASK)
async def observe_project_task(payload: ProjectObservationPayload) -> None:
    """Observe PRs using a saved project connection. No external writes."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError("pipeline.observe_project requires a schedule task context")
    service = PipelineObservationService(
        PipelineObservationRepository(), ConnectorCredentialCipher(get_credential_key_provider())
    )
    await service.observe_project_and_save(payload, meta.config_id)


@task(name=PROJECT_DISPATCH_TASK)
async def dispatch_project_task(payload: ProjectDispatchPayload) -> None:
    """Observe ready PR runs, then admit a separate bounded batch of dispatches."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError(f"{PROJECT_DISPATCH_TASK} requires a schedule task context")
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    pipeline_repo = PipelineObservationRepository()
    observer = PipelineObservationService(pipeline_repo, cipher)
    project_service = ProjectService(ProjectRepository())
    run_repo = PipelineRunRepository()
    run_use_case = PipelineRunUseCase(run_repo, project_service, observer, AICatalogService(AICatalogRepository()))

    batch_limit = get_scheduler_defaults().MAX_CONCURRENT_TASKS
    semaphore = asyncio.Semaphore(batch_limit)

    async def advance_one(run) -> None:
        """Advance one run; what GitHub or the catalog asks the run to wait for is not a failure of the tick."""
        try:
            await advance_leased(run)
        except GitHubObservationError as exc:
            if exc.kind not in WAITABLE_GITHUB_FAILURES:
                raise
            await run_use_case.wait_for_github(run.id, kind=exc.kind, retry_after=exc.retry_after)
        except ProjectError as exc:
            if exc.code == CATALOG_HOLD_CODE:
                return
            kind = exc.code.removeprefix("GITHUB_").lower()
            if kind not in WAITABLE_GITHUB_FAILURES:
                raise
            await run_use_case.wait_for_github(run.id, kind=kind, retry_after=None)
        else:
            if run.pause_reason == GITHUB_AUTH_WAIT_REASON:
                await run_use_case.clear_github_auth_wait(run.id)

    async def advance_leased(run) -> None:
        async with semaphore:
            owner = f"job:{meta.run_id}:{run.id.hex[:8]}"
            if run.state == PipelineRunState.QUEUED:
                lease = await run_use_case.acquire_lease(run.id, LeaseRequest(owner=owner, ttl_seconds=120))
                try:
                    await run_use_case.prepare_implementation(
                        run.id,
                        PrepareImplementationAttempt(
                            owner=owner,
                            token=lease.token,
                            expected_run_revision=lease.run_revision,
                        ),
                    )
                finally:
                    await run_use_case.release_lease(run.id, LeaseMutation(owner=owner, token=lease.token))
            elif run.state in (
                PipelineRunState.DISPATCHING,
                PipelineRunState.IMPLEMENTING,
                PipelineRunState.AWAITING_CI,
            ):
                lease = await run_use_case.acquire_lease(run.id, LeaseRequest(owner=owner, ttl_seconds=120))
                try:
                    if run.state == PipelineRunState.DISPATCHING:
                        await run_use_case.dispatch_implementation(run.id, owner=owner, token=lease.token)
                    else:
                        await run_use_case.advance_run(run.id, owner=owner, token=lease.token, observer=observer)
                finally:
                    await run_use_case.release_lease(run.id, LeaseMutation(owner=owner, token=lease.token))

    # Each phase has its own selection budget. Query dispatch only after observation
    # commits, so a full observation batch cannot starve it or hide newly ready runs.
    results = []
    for states in (
        (PipelineRunState.IMPLEMENTING, PipelineRunState.AWAITING_CI),
        (PipelineRunState.QUEUED, PipelineRunState.DISPATCHING),
    ):
        async with AsyncTransaction() as session:
            runs = await run_repo.list_active(
                session,
                payload.project_id,
                limit=batch_limit,
                ready_at=get_current_utc_time(),
                states=states,
            )
            if any(run.state == PipelineRunState.QUEUED for run in runs):
                limit = await _project_run_limit(session, project_service, payload.project_id)
                if limit is not None:
                    started = await run_repo.count_started(session, payload.project_id)
                    runs = _within_limit(runs, limit - started)
        # Finish every worker and its lease cleanup even when another worker fails.
        results.extend(await asyncio.gather(*(advance_one(run) for run in runs), return_exceptions=True))
    for result in results:
        if isinstance(result, BaseException):
            raise result


async def _project_run_limit(session, project_service: ProjectService, project_id) -> int | None:
    project = ProjectRead.model_validate(await project_service.get(session, project_id))
    return project.github.automation.max_in_flight_runs if project.github is not None else None


def _within_limit(runs, free: int):
    """Hold queued runs back once the project has its limit of runs with an agent or in CI."""
    free = max(0, free)
    admitted = []
    for run in runs:
        if run.state == PipelineRunState.QUEUED:
            if free == 0:
                continue
            free -= 1
        admitted.append(run)
    return admitted
