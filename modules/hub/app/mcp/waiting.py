"""Bounded long polling so agents can follow background work without their own poll loops."""

import asyncio
from collections.abc import Awaitable, Callable, Hashable
from time import monotonic

# Each read opens and closes its own transaction, so a waiting call holds no connection between polls.
POLL_INTERVAL_SECONDS = 2.0


async def wait_for_change[T](
    read: Callable[[], Awaitable[T]],
    fingerprint: Callable[[T], Hashable],
    settled: Callable[[T], bool],
    seconds: int,
) -> T:
    """Return as soon as ``fingerprint`` changes, the value settles, or ``seconds`` elapse."""
    current = await read()
    if seconds <= 0 or settled(current):
        return current
    initial = fingerprint(current)
    deadline = monotonic() + seconds
    while (remaining := deadline - monotonic()) > 0:
        await asyncio.sleep(min(POLL_INTERVAL_SECONDS, remaining))
        current = await read()
        if fingerprint(current) != initial or settled(current):
            break
    return current
