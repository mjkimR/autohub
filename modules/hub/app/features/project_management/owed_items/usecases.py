"""Owed-item reads: one transaction and a fixed statement count per request, never provider access."""

from typing import Annotated
from uuid import UUID

from app.features.project_management.owed_items.repos import OwedItemRepository
from app.features.project_management.owed_items.schemas import OwedItemCounts, OwedItemPage
from app.features.project_management.owed_items.services import (
    cleanup_adapters,
    counts_result,
    decode_cursor,
    page_result,
)
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.repos import ProjectRepository
from app_layer_base.core.database.transaction import AsyncTransaction
from app_layer_base.utils.time_util import get_current_utc_time
from fastapi import Depends


class OwedItemUseCase:
    def __init__(self, repo: Annotated[OwedItemRepository, Depends()]):
        self.repo = repo

    async def list(self, project_id: UUID | None, kind: str | None, cursor: str | None, limit: int) -> OwedItemPage:
        filters = {"project_id": str(project_id) if project_id else None, "kind": kind}
        after = decode_cursor(cursor, filters)
        adapters = cleanup_adapters()
        async with AsyncTransaction() as session:
            if project_id and not await ProjectRepository().get(session, project_id):
                raise ProjectError(404, "Project not found")
            rows = await self.repo.page(
                session,
                now=get_current_utc_time(),
                cleanup_adapters=adapters,
                project_id=project_id,
                kind=kind,
                after=after,
                limit=limit,
            )
            return page_result(rows, limit, filters)

    async def counts(self, project_id: UUID | None) -> OwedItemCounts:
        adapters = cleanup_adapters()
        async with AsyncTransaction() as session:
            if project_id and not await ProjectRepository().get(session, project_id):
                raise ProjectError(404, "Project not found")
            groups = await self.repo.counts(
                session, now=get_current_utc_time(), cleanup_adapters=adapters, project_id=project_id
            )
            return counts_result(groups)
