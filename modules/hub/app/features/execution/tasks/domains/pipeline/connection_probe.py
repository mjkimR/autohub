from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.configuration.connectors.repos import ConnectorRepository
from app.features.configuration.connectors.usecases.token import ReadConnectorTokenUseCase
from app.features.execution.tasks import task
from app.features.project_management.connection_tests.models import TEST_TASK
from app.features.project_management.connection_tests.repos import ConnectionTestRepository
from app.features.project_management.connection_tests.schemas import ConnectionTestPayload
from app.features.project_management.connection_tests.services import ConnectionTestService
from app.features.project_management.connection_tests.usecases import ConnectionTestUseCase
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService


@task(name=TEST_TASK)
async def connection_test_task(payload: ConnectionTestPayload) -> None:
    """Advance or clean up a connection test, independently of project auto-merge policy."""
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    observer = PipelineObservationService(ReadConnectorTokenUseCase(ConnectorRepository(), cipher).execute)
    service = ConnectionTestService(ConnectionTestRepository(), ProjectService(ProjectRepository()))
    await ConnectionTestUseCase(service, observer).advance(payload.test_id)
