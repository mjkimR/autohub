"""
Main conftest.py for test configuration and shared fixtures.

Integrates app-testing-base standard test plugins and provides
hub-specific overrides and configuration.
"""

import logging
import os
from uuid import uuid4

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
os.environ["SCHEDULER_KEY"] = "test-scheduler-key"

# Pin the in-memory calendar backend. Overridden, not defaulted: a developer's .env may set
# CALENDAR_BACKEND=google, and the suite must never reach a live calendar.
os.environ["CALENDAR_BACKEND"] = "fake"

# Register every routed model before the test database is created, including in focused test runs.
from app.router import router as _router  # noqa: F401

# Configure logging - reduce noise from SQLAlchemy and httpx
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


@pytest.fixture
def client_headers() -> dict[str, str]:
    """No credentials: the `app` fixture signs every request in as a stand-in superuser instead."""
    return {}


@pytest.fixture
def app(credential_key_provider):
    """Create FastAPI app with hub-specific credential overrides."""
    from app.auth import require_scheduler_or_user
    from app.features.configuration.connectors.crypto import get_credential_key_provider
    from app.main import create_app
    from app_prebuilt_user.deps import get_current_user
    from app_prebuilt_user.models import User

    application = create_app()
    application.dependency_overrides[get_credential_key_provider] = lambda: credential_key_provider
    # Tests exercise features, not signing in; `tests/e2e/test_auth` removes these to test the real thing.
    application.dependency_overrides[get_current_user] = lambda: User(
        id=uuid4(), firstname="Test", email="operator@example.com", is_active=True, is_superadmin=True
    )
    application.dependency_overrides[require_scheduler_or_user] = lambda: None
    yield application
    application.dependency_overrides.clear()
