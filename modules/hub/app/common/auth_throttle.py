"""Addresses for the failed-login lockout (the lockout itself is `app_prebuilt_user.throttle`)."""


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
