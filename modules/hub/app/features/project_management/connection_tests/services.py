import asyncio
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from app.features.ai_catalogs.providers.errors import ProviderRequestError
from app.features.project_management.connection_tests.adapters.base import TestContext
from app.features.project_management.connection_tests.adapters.registry import adapter_for
from app.features.project_management.connection_tests.catalogs import select_catalog
from app.features.project_management.connection_tests.configuration import describe_configuration
from app.features.project_management.connection_tests.github import ConnectionTestGitHub
from app.features.project_management.connection_tests.models import ACTIVE, ConnectionTest
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines import services as pipeline_services
from app.features.project_management.pipelines.github import GitHubObservationError
from app.features.project_management.pipelines.services import PipelineConfigurationError, PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.schemas import ProjectRead
from app.features.project_management.projects.services import ProjectService
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


class ConnectionTestService:
    def __init__(
        self, repo: Annotated[ConnectionTestRepository, Depends()], projects: Annotated[ProjectService, Depends()]
    ):
        self.repo, self.projects = repo, projects

    async def get(self, session: AsyncSession, project_id: UUID, test_id: UUID) -> ConnectionTest:
        row = await self.repo.get(session, test_id)
        if row is None or row.project_id != project_id:
            raise ProjectError(404, "Connection test not found")
        return row

    async def create(
        self, session: AsyncSession, project_id: UUID, request_id: UUID, catalog_id: UUID | None = None
    ) -> ConnectionTest:
        model = await self.projects.get(session, project_id, lock=True)
        project = ProjectRead.model_validate(model)
        existing = await self.repo.get(session, request_id)
        if existing is not None:
            if existing.project_id != project_id:
                raise ProjectError(409, "Request ID belongs to another project")
            if catalog_id is not None and existing.ai_catalog_id != catalog_id:
                raise ProjectError(409, "Request ID belongs to another AI catalog")
            return existing
        if not project.enabled or project.github is None:
            raise ProjectError(422, "Enable this project and configure GitHub before testing")
        if any(row.status == ACTIVE for row in await self.repo.list(session, project_id)):
            raise ProjectError(409, "A connection test is already running")
        catalog = await select_catalog(session, model, catalog_id)
        option = await describe_configuration(session, project, catalog)
        assert option is not None
        return await self.repo.create(
            session,
            ConnectionTest(
                id=request_id,
                project_id=project_id,
                project_revision=project.revision,
                repository=project.github.repository,
                connector_id=project.github.github_connector_id,
                ai_catalog_id=catalog.id,
                catalog_snapshot={
                    "configuration_fingerprint": option.configuration_fingerprint,
                    "test_spec": option.spec.model_dump(mode="json"),
                    "id": str(catalog.id),
                    "key": catalog.key,
                    "name": catalog.name,
                    "kind": catalog.kind,
                    "adapter": catalog.adapter,
                    "revision": catalog.revision,
                    "connector_id": str(catalog.connector_id) if catalog.connector_id else None,
                },
                verification=project.github.verification.model_dump(mode="json"),
                deadline=get_current_utc_time() + timedelta(hours=1),
            ),
        )

    async def step(
        self, row: ConnectionTest, observer: PipelineObservationService, *, create_once: bool = False
    ) -> None:
        now = get_current_utc_time()
        if row.status == ACTIVE and row.cancel_requested:
            row.status, row.detail = "canceled", "Test canceled; an already dispatched cloud task may still finish"
        if row.status == ACTIVE and now >= as_utc(row.deadline):
            row.status, row.detail = (
                "timed_out",
                "Verification timed out; check the provider's repository access, environment and test PR CI",
            )
        if row.status != ACTIVE and row.finished_at is None:
            row.finished_at = now
        try:
            async with asyncio.timeout(60):
                token = await observer.get_token(row.connector_id, "github")
                async with pipeline_services.create_github_client(token) as client:
                    github = ConnectionTestGitHub(client)
                    adapter = adapter_for(row)
                    context = TestContext(github, observer)
                    if row.status != ACTIVE:
                        await adapter.cleanup(row, context)
                    elif row.phase == "preparing":
                        await adapter.prepare(row, context)
                    elif row.phase == "dispatching":
                        await adapter.dispatch(row, context, create_once=create_once)
                    else:
                        await adapter.observe(row, context)
        except (GitHubObservationError, ProviderRequestError, PipelineConfigurationError, TimeoutError) as exc:
            message = str(exc) or "Connection test exceeded its time budget; retrying on the next tick"
            if row.status == ACTIVE:
                row.detail = message
                if isinstance(exc, ProviderRequestError):
                    if exc.definitive_rejection:
                        row.status = "failed"
                        if create_once:
                            row.evidence["execution_finished"] = True
                            row.evidence["output_discovery_pending"] = False
                    if exc.quota_exhausted:
                        row.evidence["quota_observed_at"] = now.isoformat()
                elif (
                    isinstance(exc, GitHubObservationError)
                    and exc.status_code in (401, 403, 404, 422)
                    and exc.kind != "rate_limited"
                ):
                    row.status = "failed"
                elif isinstance(exc, PipelineConfigurationError):
                    row.status = "failed"
                    if create_once:
                        row.evidence["execution_finished"] = True
                        row.evidence["output_discovery_pending"] = False
            else:
                row.cleanup_status = "failed"
                row.evidence["cleanup_error"] = message
        if row.status != ACTIVE and row.finished_at is None:
            row.finished_at = get_current_utc_time()
        if row.cleanup_status == "completed":
            row.evidence.pop("cleanup_error", None)
