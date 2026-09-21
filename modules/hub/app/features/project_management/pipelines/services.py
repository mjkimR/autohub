import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.features.configuration.connectors.errors import ConnectorTokenError
from app.features.project_management.pipelines.github import (
    GitHubActionsReader,
    GitHubObservationError,
    create_github_client,
)
from app.features.project_management.pipelines.schemas import PipelineObservation, PipelineObservationConfig
from app_layer_base.utils.time_util import get_current_utc_time

OBSERVATION_TASK = "pipeline.observe"


class PipelineConfigurationError(ValueError):
    pass


class PipelineObservationService:
    def __init__(self, read_token: Callable[[UUID, str], Awaitable[str]]):
        self.read_token = read_token

    async def observe(self, config: PipelineObservationConfig) -> PipelineObservation:
        try:
            async with asyncio.timeout(60):
                return await self._observe(config)
        except TimeoutError:
            raise GitHubObservationError("Pipeline observation exceeded its 60-second budget") from None

    async def _observe(self, config: PipelineObservationConfig) -> PipelineObservation:
        token = await self.get_token(config.github_connector_id, "github")
        async with create_github_client(token) as client:
            reader = GitHubActionsReader(client)
            pulls = [await reader.observe_pull(config, number) for number in config.pull_numbers]
        return PipelineObservation(observed_at=get_current_utc_time(), config=config, pulls=pulls)

    async def find_pull_request(self, connector_id: UUID, repository: str, head_branch: str) -> dict[str, Any] | None:
        token = await self.get_token(connector_id, "github")
        async with create_github_client(token) as client:
            reader = GitHubActionsReader(client)
            return await reader.find_pull_request(repository, head_branch)

    async def get_pull_request(self, connector_id: UUID, repository: str, pull_number: int) -> dict[str, Any]:
        token = await self.get_token(connector_id, "github")
        async with create_github_client(token) as client:
            return await GitHubActionsReader(client)._get(f"/repos/{repository}/pulls/{pull_number}")

    async def list_pull_comments(self, connector_id: UUID, repository: str, pull_number: int) -> list[dict[str, Any]]:
        token = await self.get_token(connector_id, "github")
        async with create_github_client(token) as client:
            return await GitHubActionsReader(client).list_issue_comments(repository, pull_number)

    async def get_token(self, connector_id: UUID, expected_provider: str) -> str:
        try:
            return await self.read_token(connector_id, expected_provider)
        except ConnectorTokenError as exc:
            raise PipelineConfigurationError(str(exc)) from None
