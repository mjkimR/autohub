"""Hub pins the effective workflow definition independently of devkit's binding format."""

from app.features.project_management.pipeline_runs.requests import request_digest
from app.features.project_management.projects.errors import ProjectError


def workflow_hash(definition: dict) -> str:
    """Hash semantic JSON, excluding checkout paths and per-unit binding/report metadata.

    Current devkit bindings identify a workflow by name; Hub still fences mid-run definition changes.
    The same definition shown by id or by unit must hash equally, including effective policy and stage switches.
    """
    if not isinstance(definition.get("id"), str) or not isinstance(definition.get("stages"), list):
        raise ProjectError(422, "Unsupported sdd workflow definition")
    return request_digest(
        {key: value for key, value in definition.items() if key not in {"path", "binding", "ok", "errors", "hash"}}
    )
