"""Access-log hardening for endpoints that receive credentials in the URL."""

from __future__ import annotations

import logging
from typing import ClassVar


class GoogleOAuthCallbackFilter(logging.Filter):
    """Remove the Google authorization response query from Uvicorn access logs."""

    callback_path: ClassVar[str] = "/api/v1/auth/google/callback"

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) < 5:
            return True
        request_target = args[2]
        if not isinstance(request_target, str):
            return True
        path, separator, _query = request_target.partition("?")
        if separator and path == self.callback_path:
            sanitized = list(args)
            sanitized[2] = path
            record.args = tuple(sanitized)
        return True


def configure_access_logging() -> None:
    """Install the callback sanitizer once for this application process."""

    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, GoogleOAuthCallbackFilter) for item in logger.filters):
        logger.addFilter(GoogleOAuthCallbackFilter())
