from typing import Annotated

from app_prebuilt_auth.api_key.deps import machine_key_header
from app_prebuilt_auth.api_key.schemas import MachinePrincipal
from app_prebuilt_auth.api_key.usecases import ApiKeyUseCase
from fastapi import Depends

from .errors import FlowError

FLOW_READ = "autohub:task:read"
FLOW_WRITE = "autohub:task:write"
FLOW_APPROVE = "autohub:task:approve"
FLOW_SCOPES = frozenset({FLOW_READ, FLOW_WRITE, FLOW_APPROVE})


async def get_flow_principal(
    keys: Annotated[ApiKeyUseCase, Depends()],
    key: Annotated[str | None, Depends(machine_key_header)] = None,
) -> MachinePrincipal:
    if not key:
        raise FlowError(401, "unauthorized", "a managed task machine key is required")
    return await keys.authenticate(key)


def require_scope(principal: MachinePrincipal, scope: str):
    if scope not in principal.scopes:
        raise FlowError(403, "task-scope", f"machine lacks {scope}")
