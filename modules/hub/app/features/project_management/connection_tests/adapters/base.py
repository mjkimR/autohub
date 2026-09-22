from dataclasses import dataclass
from typing import Protocol

from app.features.project_management.connection_tests.adapters.specs import ConnectionTestSpec
from app.features.project_management.connection_tests.github import ConnectionTestGitHub
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.pipelines.services import PipelineObservationService


@dataclass(frozen=True)
class TestContext:
    github: ConnectionTestGitHub
    observer: PipelineObservationService


class ConnectionTestAdapter(Protocol):
    spec: ConnectionTestSpec

    async def prepare(self, row: ConnectionTest, context: TestContext) -> None: ...
    async def dispatch(self, row: ConnectionTest, context: TestContext, *, create_once: bool) -> None: ...
    async def observe(self, row: ConnectionTest, context: TestContext) -> None: ...
    async def cleanup(self, row: ConnectionTest, context: TestContext) -> None: ...
