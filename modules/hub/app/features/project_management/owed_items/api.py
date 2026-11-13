from typing import Annotated
from uuid import UUID

from app.features.project_management.owed_items.schemas import OwedItemCounts, OwedItemKind, OwedItemPage
from app.features.project_management.owed_items.usecases import OwedItemUseCase
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/owed-items", tags=["Owed items"])


@router.get("", response_model=OwedItemPage)
async def list_owed_items(
    use_case: Annotated[OwedItemUseCase, Depends()],
    project_id: UUID | None = None,
    kind: OwedItemKind | None = None,
    cursor: str | None = Query(None, max_length=4096),
    limit: int = Query(50, ge=1, le=100),
):
    return await use_case.list(project_id, kind, cursor, limit)


@router.get("/counts", response_model=OwedItemCounts)
async def owed_item_counts(use_case: Annotated[OwedItemUseCase, Depends()], project_id: UUID | None = None):
    return await use_case.counts(project_id)
