"""Catalog selection and admission for isolated provider probes."""

from uuid import UUID

from app.features.ai_catalogs.models import AICatalog
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.ai_catalogs.services import AICatalogService
from app.features.project_management.connection_tests.adapters.registry import adapter_for, find_adapter
from app.features.project_management.connection_tests.configuration import describe_configuration
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.pipeline_runs.usecases.catalogs import project_catalog
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from app.features.project_management.projects.schemas import ProjectRead
from app_layer_base.utils.time_util import get_current_utc_time
from sqlalchemy.ext.asyncio import AsyncSession


def supports_connection_test(kind: str, adapter: str) -> bool:
    return find_adapter(kind, adapter) is not None


async def select_catalog(session: AsyncSession, project: Project, catalog_id: UUID | None) -> AICatalog:
    catalog = await session.get(AICatalog, catalog_id) if catalog_id else await project_catalog(session, project)
    if catalog is None:
        raise ProjectError(422, "AI catalog not found")
    if not catalog.enabled or not supports_connection_test(catalog.kind, catalog.adapter):
        raise ProjectError(422, "Select an enabled catalog that supports connection tests")
    option = await describe_configuration(session, ProjectRead.model_validate(project), catalog)
    if option is None or not option.ready:
        raise ProjectError(422, "Complete the selected test recipe's connector requirements before testing")
    return catalog


async def prepare_dispatch(session: AsyncSession, row: ConnectionTest) -> tuple[bool, bool]:
    """Persist admission and provider create intent before external I/O. Return (ready, create_once)."""
    if row.ai_catalog_id is None:  # Pre-catalog Codex tests retain their original path.
        return True, False
    catalogs = AICatalogService(AICatalogRepository())
    catalog = await catalogs.repo.get(session, row.ai_catalog_id, lock=True)
    snapshot = row.catalog_snapshot or {}
    if (
        catalog is None
        or not catalog.enabled
        or catalog.adapter != snapshot.get("adapter")
        or (str(catalog.connector_id) if catalog.connector_id else None) != snapshot.get("connector_id")
    ):
        row.cancel_requested = True
        return True, False
    if not row.evidence.get("catalog_admitted"):
        try:
            admission = await catalogs.request_dispatch(
                session, catalog.id, None, f"connection-test:{row.id}", get_current_utc_time(), exclude_test_id=row.id
            )
        except ProjectError as exc:
            row.detail = exc.detail
            return False, False
        if admission.rejection:
            row.detail = admission.rejection
            return False, False
        row.evidence = {**row.evidence, "catalog_admitted": True}
    spec = adapter_for(row).spec
    create_once = spec.create_once and not row.evidence.get(
        "create_attempted", row.evidence.get("jules_create_attempted")
    )
    if create_once:
        row.evidence = {**row.evidence, "create_attempted": True, "output_discovery_pending": spec.discovers_output_pr}
    row.detail = None
    return True, create_once
