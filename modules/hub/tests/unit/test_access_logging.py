import logging

from app.access_logging import GoogleOAuthCallbackFilter, configure_access_logging


def access_record(target: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:1234", "GET", target, "1.1", 303),
        exc_info=None,
    )


def test_google_callback_query_is_removed_from_access_log() -> None:
    record = access_record("/api/v1/auth/google/callback?code=secret&state=state")

    assert GoogleOAuthCallbackFilter().filter(record) is True

    assert "code=" not in record.getMessage()
    assert "state=" not in record.getMessage()
    assert 'GET /api/v1/auth/google/callback HTTP/1.1" 303' in record.getMessage()


def test_other_request_queries_are_preserved() -> None:
    record = access_record("/api/v1/projects?status=active")

    GoogleOAuthCallbackFilter().filter(record)

    assert "?status=active" in record.getMessage()


def test_filter_installation_is_idempotent() -> None:
    logger = logging.getLogger("uvicorn.access")
    original = list(logger.filters)
    try:
        logger.filters = [item for item in logger.filters if not isinstance(item, GoogleOAuthCallbackFilter)]
        configure_access_logging()
        configure_access_logging()
        assert sum(isinstance(item, GoogleOAuthCallbackFilter) for item in logger.filters) == 1
    finally:
        logger.filters = original
