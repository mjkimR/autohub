"""Who may call the hub.

People sign in with the account of `app-prebuilt-auth` (`POST /api/v1/users/login/`) and send the access token as
`Authorization: Bearer ...`. The first superuser comes from `FIRST_USER_EMAIL` / `FIRST_USER_PASSWORD` in the
deployment's secrets and follows them on every start (`FIRST_USER_SYNC_PASSWORD`), so the secret store stays the
one place a password is changed. The database only ever holds an Argon2id hash of it.

The external scheduler cannot sign in. It holds a database-managed machine key with the autohub:dispatch scope, which opens the dispatcher trigger, so the scheduler's configuration never carries anything derived from a person's password.
"""

from typing import Annotated

from app.common.auth_throttle import caller_address, masked_address
from app.features.notifications.notifier import Notifier
from app_layer_base.core.log import logger
from app_prebuilt_auth.api_key.config import get_api_key_settings
from app_prebuilt_auth.api_key.deps import machine_key_header, require_key_admin
from app_prebuilt_auth.api_key.usecases import ApiKeyUseCase
from app_prebuilt_auth.user.config import get_auth_settings
from app_prebuilt_auth.user.deps import LoginLockoutListener, get_current_user, get_token_data, oauth2
from app_prebuilt_auth.user.exceptions import InvalidCredentialsException
from app_prebuilt_auth.user.models import User
from app_prebuilt_auth.user.repos import UserRepository
from app_prebuilt_auth.user.services import UserService
from app_prebuilt_auth.user.token_schemas import TokenPayload
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

MCP_READ = "autohub:mcp:read"
MCP_WRITE = "autohub:mcp:write"
MCP_SCOPES = frozenset({MCP_READ, MCP_WRITE})
MACHINE_SCOPES = frozenset({"autohub:dispatch"}) | MCP_SCOPES

# Every API route except signing in itself and the dispatcher trigger.
require_user = get_current_user

_optional_bearer = OAuth2PasswordBearer(tokenUrl=oauth2.model.flows.password.tokenUrl, auto_error=False)  # type: ignore[union-attr]


async def require_scheduler_or_user(
    keys: Annotated[ApiKeyUseCase, Depends()],
    key: Annotated[str | None, Depends(machine_key_header)] = None,
    token: Annotated[str | None, Depends(_optional_bearer)] = None,
) -> None:
    """Only a machine with the dispatch scope or an active signed-in person can trigger a tick."""
    if key and token:
        raise InvalidCredentialsException()
    if key:
        principal = await keys.authenticate(key)
        if "autohub:dispatch" not in principal.scopes:
            raise HTTPException(403, "The machine lacks autohub:dispatch")
        return
    if not token:
        raise InvalidCredentialsException()
    users = UserService(get_auth_settings(), UserRepository())
    payload: TokenPayload = get_token_data(token, users)
    await get_current_user(payload, users)


async def require_machine_admin(request: Request) -> None:
    root = request.headers.get("X-Root-API-Key")
    if root is not None:
        require_key_admin(get_api_key_settings(), root)
        return
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidCredentialsException()
    users = UserService(get_auth_settings(), UserRepository())
    user = await get_current_user(get_token_data(token, users), users)
    if not user.is_superadmin:
        raise HTTPException(403, "A human administrator is required")


def login_caller(request: Request) -> str:
    """The address Cloud Run appended to `X-Forwarded-For`, never one the client chose."""
    return caller_address(request.headers.get("x-forwarded-for"), request.client.host if request.client else None)


def login_lockout_listener(notifier: Annotated[Notifier, Depends()]) -> LoginLockoutListener:
    async def tell_operator(caller: str) -> None:
        logger.warning("A caller was locked out after repeated failed logins.")
        await notifier.send(
            f"Auto Hub: repeated failed logins from {masked_address(caller)}. That address is locked out for a while.",
            level="warning",
        )

    return tell_operator


CurrentUser = Annotated[User, Depends(get_current_user)]
