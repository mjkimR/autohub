"""Slows down guessing of the API key.

The key is derived from a password its owner can remember, so its strength is that password's. What keeps guessing
impractical is that a caller only gets a handful of wrong attempts before it is locked out.
"""

from collections import deque
from dataclasses import dataclass, field

MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 60
LOCKOUT_SECONDS = 300
# Bounds memory under a flood of distinct callers; the oldest entries go first.
MAX_TRACKED_CALLERS = 10_000


@dataclass
class _Caller:
    failures: deque[float] = field(default_factory=deque)
    locked_until: float = 0.0


class FailedAuthThrottle:
    """Counts wrong keys per caller in this process.

    State is per process, so with several workers a caller gets that many times the attempts; that is still a
    handful per minute. A lockout rejects every request from the caller, right key or not: checking the key
    while locked out would let guessing go on.
    """

    def __init__(self) -> None:
        self._callers: dict[str, _Caller] = {}

    def retry_after(self, caller: str, now: float) -> int | None:
        """Seconds the caller still has to wait, or None when it may try."""
        entry = self._callers.get(caller)
        if entry is None or entry.locked_until <= now:
            return None
        return max(1, int(entry.locked_until - now))

    def record_failure(self, caller: str, now: float) -> bool:
        """Note a wrong key; True when this failure starts a lockout."""
        entry = self._callers.pop(caller, None) or _Caller()
        # Re-inserted last, so the dict stays ordered by most recent failure.
        self._callers[caller] = entry
        while entry.failures and entry.failures[0] <= now - FAILURE_WINDOW_SECONDS:
            entry.failures.popleft()
        entry.failures.append(now)
        while len(self._callers) > MAX_TRACKED_CALLERS:
            self._callers.pop(next(iter(self._callers)))
        if len(entry.failures) < MAX_FAILURES:
            return False
        entry.failures.clear()
        entry.locked_until = now + LOCKOUT_SECONDS
        return True

    def reset(self) -> None:
        self._callers.clear()


def caller_address(forwarded_for: str | None, peer: str | None) -> str:
    """The address that reached the platform's front end.

    Cloud Run appends the real client address to ``X-Forwarded-For``; everything before it is whatever the client
    sent and must not be trusted, or a caller could dodge its lockout by inventing addresses. (uvicorn runs with
    ``--forwarded-allow-ips "*"`` and would report the first, client-chosen entry.)
    """
    entries = [part.strip() for part in (forwarded_for or "").split(",") if part.strip()]
    return entries[-1] if entries else (peer or "unknown")


def masked_address(address: str) -> str:
    """Enough of an address to recognize one's own network in a notice, without recording the whole of it."""
    if ":" in address:
        return ":".join(address.split(":")[:3]) + ":…"
    parts = address.split(".")
    return ".".join([*parts[:3], "x"]) if len(parts) == 4 else "unknown"
