from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.configuration.connectors.crypto import ConnectorCredentialCipher, get_credential_key_provider
from app.features.execution.tasks import task
from app.features.execution.tasks.core.context import get_task_meta
from app.features.execution.tasks.domains.jules.service import (
    JulesSessionPayload,
    JulesSessionService,
    JulesSyncPayload,
)
from app.features.project_management.pipeline_runs.repos import PipelineRunRepository
from app.features.project_management.pipeline_runs.usecases.lifecycle import PipelineRunUseCase
from app.features.project_management.pipelines.repos import PipelineObservationRepository
from app.features.project_management.pipelines.services import PipelineObservationService
from app.features.project_management.projects.repos import ProjectRepository
from app.features.project_management.projects.services import ProjectService

JULES_SESSION_TASK = "jules.session"
JULES_SYNC_TASK = "jules.sync_sessions"


def _service() -> JulesSessionService:
    cipher = ConnectorCredentialCipher(get_credential_key_provider())
    catalogs = AICatalogService(AICatalogRepository())
    observer = PipelineObservationService(PipelineObservationRepository(), cipher)
    runs = PipelineRunUseCase(PipelineRunRepository(), ProjectService(ProjectRepository()), observer, catalogs)
    return JulesSessionService(catalogs, cipher, runs)


@task(name=JULES_SESSION_TASK)
async def start_jules_session_task(payload: JulesSessionPayload) -> None:
    """Start one Jules session when the catalog's quota admits it, after refreshing its tracked sessions."""
    meta = get_task_meta()
    if meta is None:
        raise RuntimeError(f"{JULES_SESSION_TASK} requires a schedule task context")
    await _service().start(payload, meta.config_id)


@task(name=JULES_SYNC_TASK)
async def sync_jules_sessions_task(payload: JulesSyncPayload) -> None:
    """Refresh unfinished Jules sessions: finished ones release concurrency, deliver reports, and get their pull
    requests adopted into the pipeline. Starts no Jules work."""
    await _service().sync(payload.catalog_key)
