"""Keep task registration and its cached API view local to each unit test."""

import pytest
from app.features.execution.tasks.core import registry
from app.features.execution.tasks.usecases.task_spec import GetTaskSpecUseCase


@pytest.fixture(autouse=True)
def isolated_task_registry(monkeypatch):
    monkeypatch.setattr(registry, "_registry", {})
    GetTaskSpecUseCase.clear_cache()
    yield
    GetTaskSpecUseCase.clear_cache()
