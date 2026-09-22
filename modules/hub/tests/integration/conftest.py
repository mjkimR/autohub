"""Application and database composition for integration tests only."""

from uuid import uuid4

import pytest

# Register every routed model before the test database is created, including in focused test runs.
from app.router import router as _router  # noqa: F401


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
    from app_prebuilt_auth.user.deps import get_current_user
    from app_prebuilt_auth.user.models import User

    application = create_app()
    application.dependency_overrides[get_credential_key_provider] = lambda: credential_key_provider
    # Tests exercise features, not signing in; `tests/integration/auth` removes these to test the real thing.
    application.dependency_overrides[get_current_user] = lambda: User(
        id=uuid4(), firstname="Test", email="operator@example.com", is_active=True, is_superadmin=True
    )
    application.dependency_overrides[require_scheduler_or_user] = lambda: None
    yield application
    application.dependency_overrides.clear()
