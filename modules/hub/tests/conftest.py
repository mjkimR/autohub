"""
Main conftest.py for test configuration and shared fixtures.

Integrates app-testing-base standard test plugins and provides
hub-specific overrides and configuration.
"""

import logging
import os
from pathlib import Path

import pytest

pytest_plugins = [
    "app_testing_base.plugin",
    "tests.fixtures.connectors",
    "tests.fixtures.data_factory",
]

# The account and signing key the auth settings require. Overridden, not defaulted: a developer's .env holds real
# ones, and tests must neither depend on them nor sign tokens with them.
os.environ["FIRST_USER_EMAIL"] = "operator@example.com"
os.environ["FIRST_USER_PASSWORD"] = "operator-password"
os.environ["FIRST_USER_SYNC_PASSWORD"] = "true"
os.environ["SECRET_KEY"] = "test-signing-key-not-for-production"
os.environ["APP_API_KEY_ROOT_KEY"] = "root-test-credential-at-least-32-characters"

# Pin the in-memory calendar backend. Overridden, not defaulted: a developer's .env may set
# CALENDAR_BACKEND=google, and the suite must never reach a live calendar.
os.environ["CALENDAR_BACKEND"] = "fake"
os.environ["GOOGLE_AUTH_ENABLED"] = "false"

# Configure logging - reduce noise from SQLAlchemy and httpx
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def pytest_collection_modifyitems(items):
    """The directory is authoritative; markers support existing focused commands."""
    for item in items:
        tier = item.path.relative_to(Path(__file__).parent).parts[0]
        if tier not in {"unit", "integration", "e2e"}:
            raise pytest.UsageError(f"Unclassified test: {item.nodeid}")
        item.add_marker(getattr(pytest.mark, tier))
