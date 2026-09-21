from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4

from app.features.ai_catalogs.models import (
    AICatalog,
)
from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.pipeline_runs.github import read_pull_request
from app.features.project_management.pipeline_runs.models import (
    IN_FLIGHT_RUN_STATES,
    ExecutionAttempt,
    ExecutionAttemptKind,
    ExecutionAttemptState,
    PipelineRun,
    PipelineRunState,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.requests import build_implementation_request
from app.features.project_management.pipeline_runs.schemas import (
    AttachPRRequest,
    CompleteAttemptRequest,
    EnrollPullRequest,
    ExecutionAttemptRead,
    ImplementationRequest,
    LeaseGrant,
    LeaseMutation,
    LeaseRequest,
    PauseRunRequest,
    PipelineRunRead,
    PreparedImplementationAttempt,
    PrepareImplementationAttempt,
)
from app.features.project_management.pipeline_runs.usecases.catalogs import resolve_catalog
from app.features.project_management.pipeline_runs.usecases.ci import CIProgress
from app.features.project_management.pipeline_runs.usecases.control import PipelineRunControl
from app.features.project_management.pipeline_runs.usecases.delivery import PipelineRunDelivery
from app.features.project_management.pipeline_runs.usecases.implementation import ImplementationProgress
from app.features.project_management.pipeline_runs.usecases.leases import PipelineRunLeases, raise_lease_conflict
from app.features.project_management.pipeline_runs.usecases.queries import PipelineRunQueries
from app.features.project_management.pipeline_runs.usecases.transitions import (
    ACTIVE_RUN_CONFLICT,
    EXTERNAL_IMPLEMENTATION_STATUS,
    block_for_project_change,
    wait_on_github,
)
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.pipelines.github import (
    DEFAULT_RATE_LIMIT_DELAY_SECONDS,
    GITHUB_FAILURE_AUTH,
    GitHubActionsReader,
)
from app.features.project_management.pipelines.services import PipelineConfigurationError, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.services import ProjectService
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

GITHUB_AUTH_RECHECK_DELAY = timedelta(minutes=15)
GITHUB_AUTH_WAIT_REASON = (
    "Waiting on GitHub: the project's connector token was rejected (HTTP 401). Replace the token in the connector; "
    "the run continues by itself."
)


class PipelineRunUseCase:
    def __init__(
        self,
        repo: Annotated[PipelineRunRepository, Depends()],
        projects: Annotated[ProjectService, Depends()],
        observer: Annotated[PipelineObservationService, Depends()],
        ai_catalogs: Annotated[AICatalogService | None, Depends(AICatalogService)] = None,
    ):
        self.repo = repo
        self.projects = projects
        self.observer = observer
        self.ai_catalogs = ai_catalogs

    async def get(self, run_id: UUID) -> PipelineRunRead:
        return await PipelineRunQueries(self.repo).get(run_id)

    async def enroll(self, project_id: UUID, request: EnrollPullRequest) -> PipelineRunRead:
        async with AsyncTransaction() as session:
            project = await self.projects.get(session, project_id)
            if not project.enabled:
                raise ProjectError(422, "Project is disabled")
            if project.github_repository is None or project.github_connector_id is None:
                raise ProjectError(422, "Project missing GitHub connection for pipeline run")
            if await self.repo.get_active_for_pull(session, project_id, request.pull_number) is not None:
                raise ProjectError(409, ACTIVE_RUN_CONFLICT)
            repository, connector_id, expected_revision = (
                project.github_repository,
                project.github_connector_id,
                project.revision,
            )

        # Keep GitHub reads outside database transactions.
        try:
            token = await self.observer.get_token(connector_id, "github")
        except PipelineConfigurationError as exc:
            raise ProjectError(422, str(exc)) from None
        try:
            async with asyncio.timeout(30):
                async with pipeline_services.create_github_client(token) as client:
                    snapshot = await read_pull_request(GitHubActionsReader(client), repository, request.pull_number)
        except TimeoutError:
            raise ProjectError(504, "Pull request read exceeded its time budget") from None

        try:
            async with AsyncTransaction() as session:
                project = await self.projects.get(session, project_id, lock=True)
                if not project.enabled:
                    raise ProjectError(422, "Project is disabled")
                if project.revision != expected_revision:
                    raise ProjectError(409, "Project changed during pull request enrollment; retry")
                if await self.repo.get_active_for_pull(session, project_id, snapshot.number, lock=True) is not None:
                    raise ProjectError(409, ACTIVE_RUN_CONFLICT)
                catalog = await self.resolve_catalog(session, project, request.catalog)
                run = await self.repo.create(
                    session,
                    PipelineRun(
                        project_id=project_id,
                        ai_catalog_id=catalog.id,
                        requested_catalog_id=catalog.id if request.catalog is not None else None,
                        project_revision=project.revision,
                        github_repository=project.github_repository,
                        github_connector_id=project.github_connector_id,
                        pull_number=snapshot.number,
                        pull_url=snapshot.url,
                        pull_snapshot=snapshot.model_dump(mode="json"),
                        state=PipelineRunState.AWAITING_CI if request.implemented else PipelineRunState.QUEUED,
                        branch=snapshot.head_ref,
                        revision=1,
                    ),
                )
                if request.implemented:
                    await self._record_external_implementation(session, run, repository)
                return PipelineRunRead.model_validate(run)
        except IntegrityError:
            raise ProjectError(409, ACTIVE_RUN_CONFLICT) from None

    async def _record_external_implementation(self, session: AsyncSession, run: PipelineRun, repository: str) -> None:
        """Adopt a pull request implemented outside the pipeline: its attempt is already running, nothing is sent.

        The attempt carries the standard implementation request so a CI failure can derive a fix request from it,
        which the project's catalog then delivers as usual.
        """
        implementation_request, digest, idempotency_key = build_implementation_request(run, repository)
        await self.repo.create_attempt(
            session,
            ExecutionAttempt(
                pipeline_run_id=run.id,
                attempt_number=await self.repo.next_attempt_number(session, run.id),
                epoch=run.epoch,
                kind=ExecutionAttemptKind.IMPLEMENTATION,
                state=ExecutionAttemptState.RUNNING,
                request_snapshot=implementation_request.model_dump(mode="json"),
                request_digest=digest,
                idempotency_key=idempotency_key,
                external_status=EXTERNAL_IMPLEMENTATION_STATUS,
                started_at=get_current_utc_time(),
            ),
        )

    async def prepare_implementation(
        self, run_id: UUID, request: PrepareImplementationAttempt
    ) -> PreparedImplementationAttempt:
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get_leased(
                session,
                run_id,
                owner=request.owner,
                token=request.token,
                now=now,
            )
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "prepare attempt")
            project = await self.projects.get(session, run.project_id)
            if not project.enabled or project.revision != run.project_revision:
                raise ProjectError(409, "Project changed after this pipeline run was enrolled")
            existing = await self.repo.active_attempt(session, run_id)
            if existing is not None:
                _, digest, _ = build_implementation_request(
                    run, self._github_repository(project), idempotency_key=existing.idempotency_key
                )
                if existing.request_digest != digest:
                    raise ProjectError(409, "The active attempt was prepared with a different request")
                return PreparedImplementationAttempt(
                    attempt=ExecutionAttemptRead.model_validate(existing),
                    request=ImplementationRequest.model_validate(existing.request_snapshot),
                    run_revision=run.revision,
                    created=False,
                )
            if run.revision != request.expected_run_revision:
                raise ProjectError(409, "Pipeline run changed; reload before preparing an attempt")
            if run.state != PipelineRunState.QUEUED:
                raise ProjectError(409, "Pipeline run is not ready for an implementation attempt")
            implementation_request, digest, idempotency_key = build_implementation_request(
                run, self._github_repository(project)
            )
            attempt = await self.repo.create_attempt(
                session,
                ExecutionAttempt(
                    pipeline_run_id=run.id,
                    attempt_number=await self.repo.next_attempt_number(session, run.id),
                    epoch=run.epoch,
                    kind=ExecutionAttemptKind.IMPLEMENTATION,
                    state=ExecutionAttemptState.PLANNED,
                    request_snapshot=implementation_request.model_dump(mode="json"),
                    request_digest=digest,
                    idempotency_key=idempotency_key,
                ),
            )
            run.state = PipelineRunState.DISPATCHING
            run.revision += 1
            await session.flush()
            return PreparedImplementationAttempt(
                attempt=ExecutionAttemptRead.model_validate(attempt),
                request=implementation_request,
                run_revision=run.revision,
                created=True,
            )

    async def advance_run(
        self,
        run_id: UUID,
        *,
        owner: str,
        token: UUID,
        observer: PipelineObservationService,
    ) -> PipelineRunRead:
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get_leased(
                session,
                run_id,
                owner=owner,
                token=token,
                now=now,
            )
            if run is None:
                await raise_lease_conflict(self.repo, session, run_id, "advance run")
            project = await self.projects.get(session, run.project_id)
            if (
                not project.enabled
                or project.revision != run.project_revision
                or project.github_repository is None
                or project.github_connector_id is None
            ):
                return await block_for_project_change(self.repo, session, run, now)

            # A planned delivery must be reconciled or posted before a run can advance.
            if run.state == PipelineRunState.IMPLEMENTING:
                return await ImplementationProgress(self.repo, self.ai_catalogs).advance(
                    session, run, project, now, observer
                )
            if run.state == PipelineRunState.AWAITING_CI and run.pull_number is not None:
                return await CIProgress(self.repo, self.observer).advance(session, run, project, now, observer)
            return PipelineRunRead.model_validate(run)

    async def wait_for_github(self, run_id: UUID, *, kind: str, retry_after: int | None) -> None:
        """Hold an in-flight run that GitHub would not serve, instead of failing the tick that tried.

        A rate limit only delays the run. Rejected credentials also tell the operator, once.
        """
        now = get_current_utc_time()
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is None or run.state not in IN_FLIGHT_RUN_STATES:
                return
            if kind == GITHUB_FAILURE_AUTH:
                wait_on_github(run, GITHUB_AUTH_WAIT_REASON, now, GITHUB_AUTH_RECHECK_DELAY)
            else:
                run.next_action_at = now + timedelta(seconds=retry_after or DEFAULT_RATE_LIMIT_DELAY_SECONDS)

    async def clear_github_auth_wait(self, run_id: UUID) -> None:
        async with AsyncTransaction() as session:
            run = await self.repo.get(session, run_id, lock=True)
            if run is not None and run.pause_reason == GITHUB_AUTH_WAIT_REASON:
                run.pause_reason = None
                run.revision += 1

    async def manual_advance(self, run_id: UUID, observer: PipelineObservationService) -> PipelineRunRead:
        owner = f"manual:{uuid4().hex[:8]}"
        grant = await self.acquire_lease(run_id, LeaseRequest(owner=owner, ttl_seconds=60))
        try:
            run = await self.get(run_id)
            if run.state == PipelineRunState.QUEUED:
                await self.prepare_implementation(
                    run_id,
                    PrepareImplementationAttempt(
                        owner=owner,
                        token=grant.token,
                        expected_run_revision=grant.run_revision,
                    ),
                )
                run = await self.get(run_id)
            if run.state == PipelineRunState.DISPATCHING:
                return await self.dispatch_implementation(run_id, owner=owner, token=grant.token)
            return await self.advance_run(run_id, owner=owner, token=grant.token, observer=observer)
        finally:
            await self.release_lease(run_id, LeaseMutation(owner=owner, token=grant.token))

    @staticmethod
    def _github_repository(project) -> str:
        if project.github_repository is None:
            raise ProjectError(422, "Add a GitHub connection before preparing an implementation")
        return project.github_repository

    async def acquire_lease(self, run_id: UUID, request: LeaseRequest) -> LeaseGrant:
        return await PipelineRunLeases(self.repo).acquire_lease(run_id, request)

    async def renew_lease(self, run_id: UUID, request: LeaseMutation) -> LeaseGrant:
        return await PipelineRunLeases(self.repo).renew_lease(run_id, request)

    async def release_lease(self, run_id: UUID, request: LeaseMutation) -> None:
        return await PipelineRunLeases(self.repo).release_lease(run_id, request)

    async def resolve_catalog(self, session: AsyncSession, project: Project, designation: str | None) -> AICatalog:
        return await resolve_catalog(session, project, designation)

    async def dispatch_implementation(self, run_id: UUID, *, owner: str, token: UUID) -> PipelineRunRead:
        return await PipelineRunDelivery(
            self.repo, self.projects, self.observer, self.ai_catalogs
        ).dispatch_implementation(run_id, owner=owner, token=token)

    async def pause_run(self, run_id: UUID, request: PauseRunRequest | None = None) -> PipelineRunRead:
        return await PipelineRunControl(self.repo, self.projects, self.observer).pause_run(run_id, request)

    async def resume_run(self, run_id: UUID) -> PipelineRunRead:
        return await PipelineRunControl(self.repo, self.projects, self.observer).resume_run(run_id)

    async def cancel_run(self, run_id: UUID) -> PipelineRunRead:
        return await PipelineRunControl(self.repo, self.projects, self.observer).cancel_run(run_id)

    async def attach_pr(self, run_id: UUID, request: AttachPRRequest) -> PipelineRunRead:
        return await PipelineRunControl(self.repo, self.projects, self.observer).attach_pr(run_id, request)

    async def complete_attempt(
        self, run_id: UUID, attempt_id: UUID, request: CompleteAttemptRequest
    ) -> ExecutionAttemptRead:
        return await PipelineRunControl(self.repo, self.projects, self.observer).complete_attempt(
            run_id, attempt_id, request
        )
