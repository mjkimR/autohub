from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app import auth
from app.auth import verify_api_key
from app.common.auth_throttle import (
    LOCKOUT_SECONDS,
    MAX_FAILURES,
    FailedAuthThrottle,
    caller_address,
    masked_address,
)
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def config():
    auth.failed_auth_throttle.reset()
    mock_auth_config = MagicMock()
    mock_auth_config.APP_SECRET_KEY.get_secret_value.return_value = "my-secret-key"
    with patch("app.auth.get_auth_config", return_value=mock_auth_config):
        yield mock_auth_config
    auth.failed_auth_throttle.reset()


def request_from(forwarded_for: str | None = "203.0.113.7") -> MagicMock:
    request = MagicMock()
    request.headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
    request.client.host = "10.0.0.1"
    return request


async def verify(key: str | None, *, notifier: AsyncMock | None = None, forwarded_for: str | None = "203.0.113.7"):
    await verify_api_key(request_from(forwarded_for), notifier or AsyncMock(), x_api_key=key)


async def test_verify_api_key_success():
    await verify("my-secret-key")


async def test_verify_api_key_invalid():
    with pytest.raises(HTTPException) as exc:
        await verify("wrong-key")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid or missing API key"


async def test_verify_api_key_misconfigured(config):
    config.APP_SECRET_KEY = None
    with pytest.raises(HTTPException) as exc:
        await verify("any-key")
    assert exc.value.status_code == 500
    assert exc.value.detail == "Invalid or missing API key"


async def test_repeated_wrong_keys_lock_the_caller_out_even_with_the_right_key():
    notifier = AsyncMock()
    for _ in range(MAX_FAILURES):
        with pytest.raises(HTTPException) as wrong:
            await verify("wrong-key", notifier=notifier)
        assert wrong.value.status_code == 401

    with pytest.raises(HTTPException) as locked:
        await verify("my-secret-key", notifier=notifier)

    assert locked.value.status_code == 429
    assert locked.value.headers is not None
    assert 0 < int(locked.value.headers["Retry-After"]) <= LOCKOUT_SECONDS
    # Told once, when the lockout starts, with only part of the address.
    notifier.send.assert_awaited_once()
    assert "203.0.113.x" in notifier.send.await_args.args[0] and "203.0.113.7" not in notifier.send.await_args.args[0]
    # Another caller is unaffected, and inventing forwarded addresses does not dodge the lockout.
    await verify("my-secret-key", forwarded_for="198.51.100.9")
    with pytest.raises(HTTPException) as spoofed:
        await verify("my-secret-key", forwarded_for="1.2.3.4, 203.0.113.7")
    assert spoofed.value.status_code == 429


async def test_a_request_without_a_key_is_refused_but_never_counts_toward_a_lockout():
    for _ in range(MAX_FAILURES * 2):
        with pytest.raises(HTTPException) as exc:
            await verify(None)
        assert exc.value.status_code == 401
    await verify("my-secret-key")


def test_failures_expire_and_a_lockout_ends():
    throttle = FailedAuthThrottle()
    for second in range(MAX_FAILURES - 1):
        assert throttle.record_failure("a", float(second)) is False
    # The early failures have left the window by now, so this one starts no lockout.
    assert throttle.record_failure("a", 100.0) is False
    for second in range(MAX_FAILURES - 2):
        assert throttle.record_failure("a", 101.0 + second) is False
    assert throttle.record_failure("a", 110.0) is True
    assert throttle.retry_after("a", 111.0) == LOCKOUT_SECONDS - 1
    assert throttle.retry_after("a", 110.0 + LOCKOUT_SECONDS) is None
    assert throttle.retry_after("b", 111.0) is None


def test_the_caller_is_the_address_the_platform_appended():
    assert caller_address("1.2.3.4, 203.0.113.7", "10.0.0.1") == "203.0.113.7"
    assert caller_address(None, "10.0.0.1") == "10.0.0.1"
    assert caller_address(" , ", None) == "unknown"
    assert masked_address("203.0.113.7") == "203.0.113.x"
    assert masked_address("2001:db8:85a3:8d3:1319:8a2e:370:7348") == "2001:db8:85a3:…"
