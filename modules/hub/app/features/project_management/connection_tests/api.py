from typing import Annotated
from uuid import UUID

from app.features.project_management.connection_tests.schemas import (
    ConnectionTestOption,
    ConnectionTestRead,
    StartConnectionTest,
)
from app.features.project_management.connection_tests.usecases import ConnectionTestUseCase
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/projects/{project_id}/connection-tests", tags=["Connection tests"])


@router.get("", response_model=list[ConnectionTestRead])
async def list_tests(project_id: UUID, use_case: Annotated[ConnectionTestUseCase, Depends()]):
    return await use_case.list(project_id)


@router.get("/options", response_model=list[ConnectionTestOption])
async def test_options(project_id: UUID, use_case: Annotated[ConnectionTestUseCase, Depends()]):
    return await use_case.options(project_id)


@router.post("", response_model=ConnectionTestRead, status_code=201)
async def start_test(
    project_id: UUID, data: StartConnectionTest, use_case: Annotated[ConnectionTestUseCase, Depends()]
):
    return await use_case.start(project_id, data.request_id, data.ai_catalog_id)


@router.post("/{test_id}/advance", response_model=ConnectionTestRead)
async def advance_test(project_id: UUID, test_id: UUID, use_case: Annotated[ConnectionTestUseCase, Depends()]):
    await use_case.get(project_id, test_id)
    await use_case.advance(test_id)
    return await use_case.get(project_id, test_id)


@router.post("/{test_id}/cancel", response_model=ConnectionTestRead)
async def cancel_test(project_id: UUID, test_id: UUID, use_case: Annotated[ConnectionTestUseCase, Depends()]):
    return await use_case.cancel(project_id, test_id)
