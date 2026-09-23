import builtins
from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.connection_tests import recovery
from app.features.project_management.connection_tests.adapters.registry import find_adapter
from app.features.project_management.connection_tests.adapters.specs import ConnectionTestSpec
from app.features.project_management.connection_tests.catalogs import prepare_dispatch
from app.features.project_management.connection_tests.configuration import current_fingerprint, describe_configuration
from app.features.project_management.connection_tests.schemas import (
    ConnectionTestOption,
    ConnectionTestRead,
    ResolveCleanup,
)
from app.features.project_management.connection_tests.services import ConnectionTestService
from app.features.project_management.pipeline_runs.usecases.transitions import as_utc
from app.features.project_management.pipelines.deps import get_pipeline_observer
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.schemas import ProjectRead
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


class ConnectionTestUseCase:
    def __init__(
        self,
        service: Annotated[ConnectionTestService, Depends()],
        observer: Annotated[PipelineObservationService, Depends(get_pipeline_observer)],
    ):
        self.service, self.observer = service, observer

    async def list(self, project_id: UUID) -> list[ConnectionTestRead]:
        async with AsyncTransaction() as session:
            project = ProjectRead.model_validate(await self.service.projects.get(session, project_id))
            cache = {}
            result = []
            for row in await self.service.repo.list(session, project_id):
                if row.ai_catalog_id not in cache:
                    cache[row.ai_catalog_id] = await current_fingerprint(session, project, row.ai_catalog_id)
                result.append(self.read(row, cache[row.ai_catalog_id]))
            return result

    async def start(self, project_id: UUID, request_id: UUID, catalog_id: UUID | None = None) -> ConnectionTestRead:
        try:
            async with AsyncTransaction() as session:
                row = await self.service.create(session, project_id, request_id, catalog_id)
                project = ProjectRead.model_validate(await self.service.projects.get(session, project_id))
                return self.read(row, await current_fingerprint(session, project, row.ai_catalog_id))
        except IntegrityError:
            raise ProjectError(
                409,
                "A connection test is already running; refresh its status",
                fix="Read the project's running connection test instead of starting another.",
            ) from None

    async def cancel(self, project_id: UUID, test_id: UUID) -> ConnectionTestRead:
        async with AsyncTransaction() as session:
            await self.service.get(session, project_id, test_id)
            await self.service.repo.cancel(session, test_id)
        await self.advance(test_id)
        return await self.get(project_id, test_id)

    async def get(self, project_id: UUID, test_id: UUID) -> ConnectionTestRead:
        async with AsyncTransaction() as session:
            row = await self.service.get(session, project_id, test_id)
            project = ProjectRead.model_validate(await self.service.projects.get(session, project_id))
            return self.read(row, await current_fingerprint(session, project, row.ai_catalog_id))

    async def resolve_cleanup(self, project_id: UUID, test_id: UUID, request: ResolveCleanup) -> ConnectionTestRead:
        async with AsyncTransaction() as session:
            row = await self.service.get(session, project_id, test_id, lock=True)
            recovery.resolve(row, request)
        await self.advance(test_id)
        return await self.get(project_id, test_id)

    @staticmethod
    def read(row, fingerprint: str | None) -> ConnectionTestRead:
        snapshot = row.catalog_snapshot or {}
        adapter = find_adapter(snapshot.get("kind", "codex"), snapshot.get("adapter", "codex-github-mention"))
        spec = (
            ConnectionTestSpec.model_validate(snapshot["test_spec"])
            if snapshot.get("test_spec")
            else (adapter.spec if adapter else None)
        )
        return ConnectionTestRead.model_validate(row).model_copy(
            update={
                "configuration_current": bool(fingerprint and fingerprint == snapshot.get("configuration_fingerprint")),
                "cleanup_resolution_available": recovery.can_resolve(row),
                "test_spec": spec,
            }
        )

    async def options(self, project_id: UUID) -> builtins.list[ConnectionTestOption]:
        async with AsyncTransaction() as session:
            project = ProjectRead.model_validate(await self.service.projects.get(session, project_id))
            result = []
            for catalog in await AICatalogRepository().list(session):
                option = await describe_configuration(session, project, catalog)
                if option is not None:
                    result.append(option)
            return result

    async def advance(self, test_id: UUID) -> None:
        create_once = False
        async with AsyncTransaction() as session:
            claim = await self.service.repo.claim(session, test_id)
            if claim is None:
                return
            row, token = claim
            project = await self.service.projects.get(session, row.project_id)
            fingerprint = await current_fingerprint(session, ProjectRead.model_validate(project), row.ai_catalog_id)
            changed = (row.catalog_snapshot or {}).get("configuration_fingerprint")
            if row.status == "running" and (
                not project.enabled or project.revision != row.project_revision or (changed and fingerprint != changed)
            ):
                row.cancel_requested = True
            if (
                row.status == "running"
                and row.phase == "dispatching"
                and not row.cancel_requested
                and get_current_utc_time() < as_utc(row.deadline)
            ):
                ready, create_once = await prepare_dispatch(session, row)
                if not ready:
                    row.lease_token = row.lease_until = None
                    return
            await session.flush()
            # External I/O uses a detached snapshot. A concurrent cancel is never overwritten by this worker.
            session.expunge(row)
        await self.service.step(row, self.observer, create_once=create_once)
        async with AsyncTransaction() as session:
            current = await session.get(type(row), test_id, with_for_update=True)
            if current and current.cancel_requested and row.status in ("running", "succeeded"):
                row.status, row.detail = "canceled", "Test canceled while provider observation was in flight"
                row.finished_at = get_current_utc_time()
            await self.finish(session, row, token)

    async def finish(self, session: AsyncSession, row, token: UUID) -> None:
        delivered = row.evidence.get("delivered_at")
        quota = row.evidence.get("quota_observed_at")
        record_delivery = bool(delivered and not row.evidence.get("delivery_recorded"))
        record_quota = bool(quota and not row.evidence.get("quota_recorded"))
        if record_delivery:
            row.evidence["delivery_recorded"] = True
        if record_quota:
            row.evidence["quota_recorded"] = True
        if not await self.service.repo.finish_step(session, row, token) or not row.ai_catalog_id:
            return
        catalogs = AICatalogService(AICatalogRepository())
        if record_delivery:
            await catalogs.record_dispatch_delivered(
                session, row.ai_catalog_id, as_utc(datetime.fromisoformat(delivered))
            )
        if record_quota:
            await catalogs.record_quota_event(session, row.ai_catalog_id, as_utc(datetime.fromisoformat(quota)))
