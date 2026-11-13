"""Persisted request and project identity for activity publication."""

from app.features.project_management.projects.errors import ProjectError


def project_basis(project) -> dict:
    return {
        "repository": project.github_repository,
        "connector_id": str(project.github_connector_id),
        "project_revision": project.revision,
        "catalog_id": str(project.ai_catalog_id),
        "automation": project.automation,
        "enabled": project.enabled,
        "type": project.project_type,
    }


def same_request(row, actor: str, digest: str) -> None:
    if row.actor != actor or row.request_digest != digest:
        raise ProjectError(409, "Request identity already binds a different actor or payload")
