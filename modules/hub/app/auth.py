"""Who may call the hub.

People sign in with the account of `app-prebuilt-user` (`POST /api/v1/users/login/`) and send the access token as
`Authorization: Bearer ...`. The first superuser comes from `FIRST_USER_EMAIL` / `FIRST_USER_PASSWORD` in the
deployment's secrets and follows them on every start (`FIRST_USER_SYNC_PASSWORD`), so the secret store stays the
one place a password is changed. The database only ever holds an Argon2id hash of it.

The external scheduler cannot sign in. It holds its own random key, which opens the dispatcher trigger and nothing
else, so the scheduler's configuration never carries anything derived from a person's password.
"""

import secrets
from typing import Annotated

from app.common.auth_throttle import caller_address, masked_address
from app.common.config import get_scheduler_auth_config
from app.features.notifications.notifier import Notifier
from app_layer_base.core.database.deps import get_session
from app_layer_base.core.log import logger
from app_prebuilt_user.deps import LoginLockoutListener, get_current_user, get_token_data, oauth2
from app_prebuilt_user.exceptions import InvalidCredentialsException
from app_prebuilt_user.models import User
from app_prebuilt_user.services import UserService
from app_prebuilt_user.token_schemas import TokenPayload
from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

SCHEDULER_KEY_HEADER = "X-Scheduler-Key"

# Every API route except signing in itself and the dispatcher trigger.
require_user = get_current_user

scheduler_key_header = APIKeyHeader(name=SCHEDULER_KEY_HEADER, auto_error=False)
_optional_bearer = OAuth2PasswordBearer(tokenUrl=oauth2.model.flows.password.tokenUrl, auto_error=False)  # type: ignore[union-attr]


async def require_scheduler_or_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    users: Annotated[UserService, Depends()],
    scheduler_key: Annotated[str | None, Security(scheduler_key_header)] = None,
    token: Annotated[str | None, Depends(_optional_bearer)] = None,
) -> None:
    """The dispatcher trigger: the scheduler's own key, or a signed-in person pressing the button in the UI."""
    expected = get_scheduler_auth_config().SCHEDULER_KEY
    if scheduler_key:
        if expected is None or not secrets.compare_digest(scheduler_key, expected.get_secret_value()):
            raise InvalidCredentialsException()
        return
    if not token:
        raise InvalidCredentialsException()
    payload: TokenPayload = get_token_data(token, users)
    await get_current_user(payload, session, users)


def login_caller(request: Request) -> str:
    """The address Cloud Run appended to `X-Forwarded-For`, never one the client chose."""
    return caller_address(request.headers.get("x-forwarded-for"), request.client.host if request.client else None)


def login_lockout_listener(notifier: Annotated[Notifier, Depends()]) -> LoginLockoutListener:
    async def tell_operator(caller: str) -> None:
        logger.warning("A caller was locked out after repeated failed logins.")
        await notifier.send(
            f"Auto Hub: repeated failed logins from {masked_address(caller)}. That address is locked out for a while."
        )

    return tell_operator


CurrentUser = Annotated[User, Depends(get_current_user)]
