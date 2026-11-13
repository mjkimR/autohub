"""Isolate lifecycle unit scenarios from the separately tested origin database projection."""

from unittest.mock import AsyncMock

import pytest
from app.features.project_management.pipeline_runs.origin_repos import RunOriginRepository


@pytest.fixture(autouse=True)
def unlinked_origin_repository(monkeypatch):
    for method in ("work_items", "sessions", "claims"):
        monkeypatch.setattr(RunOriginRepository, method, AsyncMock(return_value=[]))
