"""Derive prerequisite checks and a connection fingerprint, excluding quota/runtime state."""

import hashlib
import json
from uuid import UUID

from app.features.ai_catalogs.models import AICatalog
from app.features.configuration.connectors.models import Connector
from app.features.project_management.connection_tests.adapters.registry import find_adapter
from app.features.project_management.connection_tests.schemas import ConnectionTestOption, RequirementStatus
from app.features.project_management.projects.schemas import ProjectRead
from sqlalchemy.ext.asyncio import AsyncSession


async def describe_configuration(
    session: AsyncSession, project: ProjectRead, catalog: AICatalog
) -> ConnectionTestOption | None:
    adapter = find_adapter(catalog.kind, catalog.adapter)
    if adapter is None:
        return None
    spec = adapter.spec
    identities = {}
    checks = []
    for requirement in spec.requirements:
        status = "manual"
        if requirement.source != "manual":
            connector_id = (
                (project.github.github_connector_id if project.github else None)
                if requirement.source == "project_github"
                else catalog.connector_id
            )
            connector = await session.get(Connector, connector_id) if connector_id else None
            valid = bool(
                connector
                and connector.enabled
                and connector.has_credentials
                and connector.provider == requirement.provider
            )
            status = "configured" if valid else "missing"
            # Only the final digest is returned or persisted. Credential rotations invalidate readiness even if
            # the connector ID is unchanged. Names and quota events are deliberately excluded.
            identities[requirement.key] = {
                "id": str(connector_id),
                "enabled": connector.enabled if connector else False,
                "provider": connector.provider if connector else None,
                "config": connector.config if connector else None,
                "key_version": connector.credential_key_version if connector else None,
                "credential_version": hashlib.sha256(
                    connector.credentials_ciphertext + connector.credentials_nonce
                ).hexdigest()
                if connector
                else None,
            }
        checks.append(RequirementStatus(key=requirement.key, status=status))
    material = {
        "recipe": {"key": spec.key, "version": spec.version, "connector_provider": spec.connector_provider},
        "catalog": str(catalog.id),
        "enabled": catalog.enabled,
        "identities": identities,
        "project_enabled": project.enabled,
        "repository": project.github.repository if project.github else None,
        "verification": project.github.verification.model_dump(mode="json") if project.github else None,
    }
    digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ConnectionTestOption(
        ai_catalog_id=catalog.id,
        name=catalog.name,
        kind=catalog.kind,
        spec=spec,
        requirements=checks,
        configuration_fingerprint=digest,
        ready=project.enabled
        and catalog.enabled
        and project.github is not None
        and all(c.status != "missing" for c in checks),
    )


async def current_fingerprint(session: AsyncSession, project: ProjectRead, catalog_id: UUID | None) -> str | None:
    catalog = await session.get(AICatalog, catalog_id) if catalog_id else None
    option = await describe_configuration(session, project, catalog) if catalog else None
    return option.configuration_fingerprint if option else None
