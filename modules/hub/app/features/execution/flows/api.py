from typing import Annotated
from uuid import UUID

from app_prebuilt_auth.api_key.schemas import MachinePrincipal
from autohub_sdk import (
    ActivationReceipt,
    ActivationRequest,
    ReleaseReceipt,
    ReleaseSpec,
    RunCommand,
    RunRequest,
    RunView,
)
from fastapi import APIRouter, Depends, Path
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from .auth import get_flow_principal
from .errors import FlowError
from .usecases import FlowUseCase


class FlowRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                raise FlowError(422, "request-invalid", "request does not match the wire schema") from exc

        return handle


router = APIRouter(tags=["SDK Flows"], route_class=FlowRoute)
Principal = Annotated[MachinePrincipal, Depends(get_flow_principal)]
UseCase = Annotated[FlowUseCase, Depends()]
Provider = Annotated[str, Path(pattern=r"^[a-z][a-z0-9_-]*$", max_length=64)]
ReleaseId = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", max_length=128)]
RELEASE_PATH = "/task-providers/{provider}/environments/{environment}/releases/{release_id}"


@router.put(RELEASE_PATH, response_model=ReleaseReceipt)
async def register(
    provider: Provider,
    environment: Provider,
    release_id: ReleaseId,
    body: ReleaseSpec,
    principal: Principal,
    use_case: UseCase,
):
    return await use_case.register(provider, environment, release_id, body, principal)


@router.post(RELEASE_PATH + "/activate", response_model=ActivationReceipt)
async def activate(
    provider: Provider,
    environment: Provider,
    release_id: ReleaseId,
    body: ActivationRequest,
    principal: Principal,
    use_case: UseCase,
):
    return await use_case.activate(provider, environment, release_id, body, principal)


@router.post("/task-runs", response_model=RunView, status_code=202)
async def start(body: RunRequest, principal: Principal, use_case: UseCase):
    return await use_case.start(body, principal)


@router.get("/task-runs/{run_id}", response_model=RunView)
async def get(run_id: UUID, principal: Principal, use_case: UseCase):
    return await use_case.get(run_id, principal)


@router.post("/task-runs/{run_id}/commands", response_model=RunView)
async def command(run_id: UUID, body: RunCommand, principal: Principal, use_case: UseCase):
    return await use_case.command(run_id, body, principal)
