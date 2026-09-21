from typing import Annotated
from uuid import UUID

from app.features.ai_catalogs.schemas import (
    AICatalogList,
    AICatalogRead,
    AICatalogSessionList,
    SessionStatusFilter,
    SetAvailabilityRequest,
    SetConnectorRequest,
    SetEnabledRequest,
    UpdatePolicyConfigRequest,
)
from app.features.ai_catalogs.usecases import AICatalogUseCase
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/ai-catalogs", tags=["AI Catalog"])


@router.get("", response_model=AICatalogList)
async def list_ai_catalogs(usecase: Annotated[AICatalogUseCase, Depends()]):
    return await usecase.list()


@router.get("/{catalog_key}/sessions", response_model=AICatalogSessionList)
async def list_ai_catalog_sessions(
    catalog_key: str,
    usecase: Annotated[AICatalogUseCase, Depends()],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    status: SessionStatusFilter | None = None,
    schedule_config_id: UUID | None = None,
):
    return await usecase.list_sessions(
        catalog_key, offset=offset, limit=limit, status=status, schedule_config_id=schedule_config_id
    )


@router.put("/{catalog_key}/availability", response_model=AICatalogRead)
async def set_ai_catalog_availability(
    catalog_key: str,
    request: SetAvailabilityRequest,
    usecase: Annotated[AICatalogUseCase, Depends()],
):
    return await usecase.set_availability(catalog_key, request)


@router.delete("/{catalog_key}/availability", response_model=AICatalogRead)
async def clear_ai_catalog_availability(
    catalog_key: str,
    usecase: Annotated[AICatalogUseCase, Depends()],
):
    return await usecase.clear_availability(catalog_key)


@router.put("/{catalog_key}/enabled", response_model=AICatalogRead)
async def set_ai_catalog_enabled(
    catalog_key: str,
    request: SetEnabledRequest,
    usecase: Annotated[AICatalogUseCase, Depends()],
):
    return await usecase.set_enabled(catalog_key, request.enabled)


@router.put("/{catalog_key}/policy-config", response_model=AICatalogRead)
async def update_ai_catalog_policy_config(
    catalog_key: str,
    request: UpdatePolicyConfigRequest,
    usecase: Annotated[AICatalogUseCase, Depends()],
):
    return await usecase.update_policy_config(catalog_key, request)


@router.put("/{catalog_key}/connector", response_model=AICatalogRead)
async def set_ai_catalog_connector(
    catalog_key: str,
    request: SetConnectorRequest,
    usecase: Annotated[AICatalogUseCase, Depends()],
):
    return await usecase.set_connector(catalog_key, request.connector_id)
