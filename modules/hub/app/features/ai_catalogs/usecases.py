from typing import Annotated
from uuid import UUID

from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.schemas import (
    AICatalogList,
    AICatalogRead,
    AICatalogSessionList,
    AICatalogSessionRead,
    SessionStatusFilter,
    SetAvailabilityRequest,
    UpdatePolicyConfigRequest,
)
from app.features.ai_catalogs.services import (
    CATALOG_CONNECTOR_PROVIDERS,
    CATALOG_SESSION_WORK_TYPES,
    AICatalogService,
)
from app.features.project_management.connection_tests.catalogs import supports_connection_test
from app.features.project_management.pipeline_runs.adapters.capabilities import supports_pipeline_delivery
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


class AICatalogUseCase:
    def __init__(
        self,
        service: Annotated[AICatalogService, Depends()],
        repo: Annotated[AICatalogRepository, Depends()],
    ) -> None:
        self.service = service
        self.repo = repo

    async def _read(self, catalog: AICatalog, session: AsyncSession) -> AICatalogRead:
        await session.refresh(catalog)
        return AICatalogRead.model_validate(catalog).model_copy(
            update={
                "held_run_count": await self.repo.held_run_count(session, catalog.id, get_current_utc_time()),
                "active_dispatch_count": await self.repo.active_dispatch_count(session, catalog.id),
                "open_session_count": await self.repo.open_session_count(session, catalog.id),
                "effective_concurrency": self.service.effective_concurrency(catalog),
                "connector_provider": CATALOG_CONNECTOR_PROVIDERS.get(catalog.kind),
                "pipeline_delivery": supports_pipeline_delivery(catalog.adapter),
                "connection_test": supports_connection_test(catalog.kind, catalog.adapter),
                "session_work_types": list(CATALOG_SESSION_WORK_TYPES.get(catalog.kind, ())),
            }
        )

    async def list(self) -> AICatalogList:
        async with AsyncTransaction() as session:
            catalogs = await self.repo.list(session)
            return AICatalogList(items=[await self._read(catalog, session) for catalog in catalogs])

    async def list_sessions(
        self,
        key: str,
        *,
        offset: int,
        limit: int,
        status: SessionStatusFilter | None = None,
        schedule_config_id: UUID | None = None,
    ) -> AICatalogSessionList:
        async with AsyncTransaction() as session:
            rows, total = await self.service.list_sessions(
                session, key, offset=offset, limit=limit, status=status, schedule_config_id=schedule_config_id
            )
            return AICatalogSessionList(
                items=[AICatalogSessionRead.model_validate(row) for row in rows], total_count=total
            )

    async def set_availability(self, key: str, request: SetAvailabilityRequest) -> AICatalogRead:
        async with AsyncTransaction() as session:
            catalog = await self.service.set_availability(session, key, request, get_current_utc_time())
            return await self._read(catalog, session)

    async def clear_availability(self, key: str) -> AICatalogRead:
        async with AsyncTransaction() as session:
            catalog = await self.service.clear_availability(session, key, get_current_utc_time())
            return await self._read(catalog, session)

    async def set_enabled(self, key: str, enabled: bool) -> AICatalogRead:
        async with AsyncTransaction() as session:
            catalog = await self.service.set_enabled(session, key, enabled, get_current_utc_time())
            return await self._read(catalog, session)

    async def update_policy_config(self, key: str, request: UpdatePolicyConfigRequest) -> AICatalogRead:
        async with AsyncTransaction() as session:
            catalog = await self.service.update_policy_config(session, key, request)
            return await self._read(catalog, session)

    async def set_connector(self, key: str, connector_id: UUID | None) -> AICatalogRead:
        async with AsyncTransaction() as session:
            catalog = await self.service.set_connector(session, key, connector_id)
            return await self._read(catalog, session)
