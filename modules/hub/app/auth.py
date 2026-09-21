import secrets
import time
from typing import Annotated

from app.common.auth_throttle import LOCKOUT_SECONDS, MAX_FAILURES, FailedAuthThrottle, caller_address, masked_address
from app.common.config import get_auth_config
from app.features.notifications.notifier import Notifier
from app_layer_base.core.log import logger
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
failed_auth_throttle = FailedAuthThrottle()


async def verify_api_key(
    request: Request,
    notifier: Annotated[Notifier, Depends()],
    x_api_key: str | None = Security(api_key_header),
) -> None:
    """Verify the API key provided in the request header.

    About the SHA-256 (a deliberate choice, not a hashing-at-rest scheme): the operator signs in with a password
    they can remember. The UI and the setup scripts hash it once, and that digest *is* the API key: it is what the
    browser stores, what Cloud Scheduler sends, and what ``APP_SECRET_KEY`` holds, so the comparison below is a
    plain constant-time equality. The hash only keeps the password itself out of browser storage, scheduler
    configuration, and Secret Manager. It adds no strength: whoever reads the stored digest can authenticate, and
    the key is as guessable as the password. Guessing is held off by the lockout in ``auth_throttle``, not by the
    hash. Do not "fix" this by hashing again on the server or by storing a salted hash: every client sends the
    digest, so that would only break them.

    Usage:
        APIRouter(..., dependencies=[Depends(verify_api_key)])
    """
    secret_key = get_auth_config().APP_SECRET_KEY
    if not secret_key:
        logger.error("Authentication misconfigured: APP_SECRET_KEY is not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid or missing API key",
        )
    caller = caller_address(request.headers.get("x-forwarded-for"), request.client.host if request.client else None)
    now = time.monotonic()
    retry_after = failed_auth_throttle.retry_after(caller, now)
    if retry_after is not None:
        # Rejected before the key is looked at: a locked-out caller learns nothing, right key or not.
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts; try again later",
            headers={"Retry-After": str(retry_after)},
        )
    if not x_api_key:
        # No guess was made (a signed-out tab, a probe): refuse it without counting toward a lockout.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    if not secrets.compare_digest(x_api_key, secret_key.get_secret_value()):
        if failed_auth_throttle.record_failure(caller, now):
            logger.warning("A caller was locked out after repeated wrong API keys.")
            await notifier.send(
                f"Auto Hub: {MAX_FAILURES} wrong API keys in a row from {masked_address(caller)}. "
                f"That address is locked out for {LOCKOUT_SECONDS // 60} minutes."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
