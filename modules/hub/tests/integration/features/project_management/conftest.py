from contextlib import asynccontextmanager
from contextvars import ContextVar

import pytest
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher
from app.features.configuration.connectors.usecases import token as token_usecase
from app.features.project_management.pipeline_runs.usecases import progress
from app.features.project_management.pipelines import services


@pytest.fixture
def verify_observation_io_scope(monkeypatch):
    """Assert both credential decryption and every GitHub request happen outside owned transactions."""
    depth = ContextVar("observation_transaction_depth", default=0)
    original_tx = progress.AsyncTransaction

    @asynccontextmanager
    async def tracked_transaction():
        scope = depth.set(depth.get() + 1)
        try:
            async with original_tx() as session:
                yield session
        finally:
            depth.reset(scope)

    monkeypatch.setattr(progress, "AsyncTransaction", tracked_transaction)
    monkeypatch.setattr(token_usecase, "AsyncTransaction", tracked_transaction)
    decrypt = ConnectorCredentialCipher.decrypt

    async def checked_decrypt(self, *args, **kwargs):
        assert depth.get() == 0, "Credential decryption held a database transaction"
        return await decrypt(self, *args, **kwargs)

    monkeypatch.setattr(ConnectorCredentialCipher, "decrypt", checked_decrypt)

    def install():
        # Capture the test's HTTP fixture after it is installed.
        create_client = services.create_github_client

        async def checked_request(request):
            assert depth.get() == 0, "GitHub I/O held a database transaction"

        def checked_client(token):
            client = create_client(token)
            client.event_hooks["request"].append(checked_request)
            return client

        monkeypatch.setattr(services, "create_github_client", checked_client)

    return install


@pytest.fixture
def isolated_sqlite_dispatch(session, monkeypatch):
    """SQLite's in-memory StaticPool shares one connection across concurrent transactions.

    Serialize this observation test's jobs; PostgreSQL retains real concurrent dispatch.
    Maintenance and retention have their own integration coverage.
    """
    if session.get_bind().dialect.name == "sqlite":
        from app.features.execution.dispatchers import services as dispatchers

        settings = dispatchers.get_scheduler_defaults().model_copy(update={"MAX_CONCURRENT_TASKS": 1})
        monkeypatch.setattr(dispatchers, "get_scheduler_defaults", lambda: settings)
