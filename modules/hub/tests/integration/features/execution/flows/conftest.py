"""Optional disposable loopback PostgreSQL instead of Docker for these tests."""

import inspect
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.features.execution.flows.adapters import HttpTarget, WorkerBindings, get_worker_bindings
from app.features.execution.flows.auth import FLOW_SCOPES, get_flow_principal
from app_prebuilt_auth.api_key.schemas import MachinePrincipal
from app_testing_base.db.fixtures import db_url as standard_db_url
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session")
def db_url(db_type):
    external = os.getenv("AUTOHUB_FLOW_TEST_POSTGRES_URL")
    if external and db_type in ("postgres", "postgresql", "pg"):
        url = make_url(external)
        if url.host != "127.0.0.1" or not (url.database or "").startswith("autohub_test_"):
            raise ValueError("flow test override requires a disposable loopback autohub_test_ database")
        yield external
    else:
        yield from inspect.unwrap(standard_db_url)(db_type)


@pytest.fixture
def owner(app):
    principal = MachinePrincipal(machine_id=uuid4(), key_id=uuid4(), name="planhub", scopes=FLOW_SCOPES)
    app.dependency_overrides[get_flow_principal] = lambda: principal
    app.dependency_overrides[get_worker_bindings] = lambda: WorkerBindings(
        {"worker": HttpTarget(base_url="https://worker.test")}
    )
    return principal


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        now = datetime(2026, 10, 9, tzinfo=UTC)

        def advance(self, seconds=6):
            self.now += timedelta(seconds=seconds)

    clock = Clock()
    monkeypatch.setattr("app.features.execution.flows.worker.get_current_utc_time", lambda: clock.now)
    monkeypatch.setattr("app.features.execution.flows.services.get_current_utc_time", lambda: clock.now)
    return clock
