"""Explicit construction for MCP calls; no FastAPI dependency resolution."""

from uuid import UUID

from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.ai_catalogs.usecases import AICatalogUseCase
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.services import ConnectorService
from app.features.configuration.connectors.usecases.crud import GetMultiConnectorUseCase
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.connection_tests.services import ConnectionTestService
from app.features.project_management.connection_tests.usecases import ConnectionTestUseCase
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipeline_runs.usecases.queries import PipelineRunQueries
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService
from app.features.project_management.projects.usecases.crud import ProjectUseCase


async def read_token(connector_id: UUID, provider: str) -> str:
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    return await ReadConnectorTokenUseCase(ConnectorRepository(), cipher).execute(connector_id, provider)


def connector_reader() -> GetMultiConnectorUseCase:
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    return GetMultiConnectorUseCase(ConnectorService(ConnectorRepository(), cipher))


class Dependencies:
    def __init__(self) -> None:
        projects = ProjectService(ProjectRepository())
        runs = PipelineRunRepository()
        catalog_repo = AICatalogRepository()
        catalogs = AICatalogService(catalog_repo)
        observer = PipelineObservationService(read_token)
        self.projects = ProjectUseCase(projects)
        self.runs = PipelineRunUseCase(runs, projects, observer, catalogs)
        self.queries = PipelineRunQueries(runs)
        self.catalogs = AICatalogUseCase(catalogs, catalog_repo)
        self.tests = ConnectionTestUseCase(ConnectionTestService(ConnectionTestRepository(), projects), observer)
