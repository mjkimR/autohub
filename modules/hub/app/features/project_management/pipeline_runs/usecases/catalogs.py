from __future__ import annotations

from app.features.ai_catalogs.models import (
    AICatalog,
    AICatalogKind,
    AICatalogState,
)
from app.features.ai_catalogs.repos import AICatalogRepository
from app.features.project_management.pipeline_runs.adapters.capabilities import supports_pipeline_delivery
from app.features.project_management.pipeline_runs.adapters.codex_github_mention import CodexGithubMentionAdapter
from app.features.project_management.pipeline_runs.models import (
    PipelineRun,
)
from app.features.project_management.projects.errors import ProjectError
from app.features.project_management.projects.models import Project
from sqlalchemy.ext.asyncio import AsyncSession


async def resolve_catalog(session: AsyncSession, project: Project, designation: str | None) -> AICatalog:
    """The catalog for new pull request work: the designated one, else the project's selection.

    A designation is a catalog key, or a kind when exactly one enabled catalog has it. This is the one place
    that maps a request to a catalog, so a router can replace it later.
    """
    if designation is None:
        return await project_catalog(session, project)
    catalogs = AICatalogRepository()
    catalog = await catalogs.get_by_key(session, designation)
    if catalog is None:
        candidates = [item for item in await catalogs.list_by_kind(session, designation.lower()) if item.enabled]
        if len(candidates) > 1:
            keys = ", ".join(item.key for item in candidates)
            raise ProjectError(422, f"'{designation}' matches several AI catalogs ({keys}); name one by key")
        if not candidates:
            raise ProjectError(422, f"No AI catalog is named or of kind '{designation}'")
        catalog = candidates[0]
    if not catalog.enabled:
        raise ProjectError(422, f"AI catalog '{catalog.key}' is disabled")
    if not supports_pipeline_delivery(catalog.adapter):
        raise ProjectError(422, f"AI catalog '{catalog.key}' cannot deliver pull request work")
    return catalog


async def run_catalog(session: AsyncSession, project: Project, run: PipelineRun) -> AICatalog:
    """A run's catalog for further deliveries: its designated catalog while that is usable, else the project's."""
    if run.requested_catalog_id is not None:
        requested = await AICatalogRepository().get(session, run.requested_catalog_id)
        if requested is not None and requested.enabled and supports_pipeline_delivery(requested.adapter):
            return requested
    return await project_catalog(session, project)


async def project_catalog(session: AsyncSession, project: Project) -> AICatalog:
    """The catalog for a project's pull request work: its selection, else the seeded Codex catalog.

    The seeded catalog is created on demand for metadata-only test databases.
    """
    catalogs = AICatalogRepository()
    if project.ai_catalog_id is not None:
        selected = await catalogs.get(session, project.ai_catalog_id)
        if selected is None:
            raise ProjectError(409, "The project's AI catalog was removed; select another one")
        return selected
    catalog = await catalogs.get_by_key(session, "personal-codex", lock=True)
    if catalog is None:
        catalog = AICatalog(
            key="personal-codex",
            name="Personal Codex",
            kind=AICatalogKind.CODEX,
            adapter=CodexGithubMentionAdapter.key,
            enabled=True,
            availability_state=AICatalogState.NORMAL,
            revision=1,
        )
        session.add(catalog)
        await session.flush()
    return catalog
