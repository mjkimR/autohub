import asyncio

from app.common.config import get_scheduler_defaults
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.execution.tasks import task
from app.features.execution.tasks.core.context import get_task_meta
from app.features.project_management.pipeline_runs.models import PipelineRunState
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.schemas import PipelineRunRead
from app.features.project_management.pipeline_runs.usecases.delivery import CATALOG_HOLD_CODE
from app.features.project_management.pipeline_runs.usecases.lifecycle import (
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
from app.features.project_management.pipelines.usecases.observation import ObservePipelineUseCase
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
from app.features.project_management.work_plans.execution import WorkPlanExecution
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
        ReadConnectorTokenUseCase(
            ConnectorRepository(), ConnectorCredentialCipher(get_credential_key_provider())
        ).execute
    )
    await ObservePipelineUseCase(service, PipelineObservationRepository()).observe_and_save(payload, meta.config_id)


@task(name=PROJECT_OBSERVATION_TASK)
async def observe_project_task(payload: ProjectObservationPayload) -> None:
    """Observe PRs using a saved project connection. No external writes."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError("pipeline.observe_project requires a schedule task context")
    service = PipelineObservationService(
        ReadConnectorTokenUseCase(
            ConnectorRepository(), ConnectorCredentialCipher(get_credential_key_provider())
        ).execute
    )
    await ObservePipelineUseCase(service, PipelineObservationRepository()).observe_project_and_save(
        payload, meta.config_id
    )


@task(name=PROJECT_DISPATCH_TASK)
async def dispatch_project_task(payload: ProjectDispatchPayload) -> None:
    """Advance active runs, then admit a separate bounded batch of new runs."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError(f"{PROJECT_DISPATCH_TASK} requires a schedule task context")
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    observer = PipelineObservationService(ReadConnectorTokenUseCase(ConnectorRepository(), cipher).execute)
    project_service = ProjectService(ProjectRepository())
    run_repo = PipelineRunRepository()
    run_use_case = PipelineRunUseCase(run_repo, project_service, observer, AICatalogService(AICatalogRepository()))

    batch_limit = get_scheduler_defaults().MAX_CONCURRENT_TASKS
    semaphore = asyncio.Semaphore(batch_limit)

    async def advance_one(run) -> bool:
        """Advance one run; what GitHub or the catalog asks the run to wait for is not a failure of the tick."""
        try:
            advanced_run = await advance_leased(run)
        except GitHubObservationError as exc:
            if exc.kind not in WAITABLE_GITHUB_FAILURES:
                raise
            await run_use_case.wait_for_github(run.id, kind=exc.kind, retry_after=exc.retry_after)
        except ProjectError as exc:
            if exc.code == CATALOG_HOLD_CODE:
                return False
            kind = exc.code.removeprefix("GITHUB_").lower()
            if kind not in WAITABLE_GITHUB_FAILURES:
                raise
            await run_use_case.wait_for_github(run.id, kind=kind, retry_after=None)
        else:
            if run.pause_reason == GITHUB_AUTH_WAIT_REASON:
                await run_use_case.clear_github_auth_wait(run.id)
            return advanced_run.state == PipelineRunState.DISPATCHING
        return False

    async def advance_leased(run) -> PipelineRunRead:
        async with semaphore:
            return await run_use_case.advance_until_wait(
                run.id, observer, owner=f"job:{meta.run_id}:{run.id.hex[:8]}", respect_due=True
            )

    # Active runs and new dispatch candidates have separate selection budgets. Start existing dispatches
    # before potentially slow work-item preparation, then fill any unused slots.
    results = []
    dispatch_count = 0
    advanced = set()
    for phase in ("observe", "dispatch", "follow_up"):
        if phase == "follow_up":
            try:
                await WorkPlanExecution(observer).advance_project(payload.project_id, limit=batch_limit)
            except Exception as exc:
                results.append(exc)
            if dispatch_count >= batch_limit:
                continue
        states = (
            (PipelineRunState.IMPLEMENTING, PipelineRunState.AWAITING_CI, PipelineRunState.PAUSED)
            if phase == "observe"
            else (PipelineRunState.QUEUED, PipelineRunState.DISPATCHING)
        )
        async with AsyncTransaction() as session:
            runs = await run_repo.list_active(
                session,
                payload.project_id,
                limit=batch_limit,
                ready_at=get_current_utc_time(),
                states=states,
                exclude_ids=tuple(advanced),
            )
            if phase != "observe":
                runs = [run for run in runs if run.id not in advanced][: batch_limit - dispatch_count]
            if any(run.state == PipelineRunState.QUEUED for run in runs):
                limit = await _project_run_limit(session, project_service, payload.project_id)
                if limit is not None:
                    started = await run_repo.count_started(session, payload.project_id)
                    runs = _within_limit(runs, limit - started)
        advanced.update(run.id for run in runs)
        if phase != "observe":
            # Holds and uncertain deliveries must not be retried in the follow-up pass.
            dispatch_count += len(runs)
        # Finish every worker and its lease cleanup even when another worker fails.
        phase_results = await asyncio.gather(*(advance_one(run) for run in runs), return_exceptions=True)
        results.extend(phase_results)
        if phase == "observe":
            # Another observation may have released catalog capacity. Reconsider committed dispatches
            # once in the bounded dispatch batch; its query still enforces quota holds and due times.
            # Failed/uncertain deliveries stay excluded, as do all candidates after that dispatch pass.
            advanced.difference_update(
                run.id for run, result in zip(runs, phase_results, strict=True) if result is True
            )
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
