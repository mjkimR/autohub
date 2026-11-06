"""Pure selection and drift decisions; no publication or execution collaborators."""

from graphlib import CycleError, TopologicalSorter

from app.features.project_management.projects.errors import ProjectError

from .milestone_graph import LIMITS, safe_path


def ordered_selection(preview: dict, requested: list[dict]) -> list[dict]:
    if not preview.get("complete") or any(
        preview["counts"].get(k, 0) > LIMITS[k] for k in ("members", "anchors", "edges")
    ):
        raise ProjectError(422, "Complete bounded milestone evidence is required")
    if not 1 <= len(requested) <= LIMITS["members"] or len({r["id"] for r in requested}) != len(requested):
        raise ProjectError(422, "Select one to fifty distinct direct members")
    available = {r["id"]: r for r in preview["members"]}
    selected = {}
    for value in requested:
        safe_path(value["path"])
        row = available.get(value["id"])
        if (
            not row
            or row["path"] != value["path"]
            or row["activity_kind"] != value["activity"]
            or row["admission"] != "pass"
            or row["eligibility"] not in ("eligible_now", "held")
            or any((row.get("workflow_hold") or {}).values())
        ):
            raise ProjectError(422, "Selection contains an unsupported or workflow-held member")
        selected[value["id"]] = {**row, "preferences": value}
    graph = {key: set() for key in selected}
    for edge in preview["edges"]:
        if edge["source"] in graph and edge.get("canonical_id") in graph:
            graph[edge["source"]].add(edge["canonical_id"])
    order = []
    try:
        sorter = TopologicalSorter(graph)
        sorter.prepare()
        while sorter.is_active():
            ready = sorted(sorter.get_ready())
            order.extend(ready)
            sorter.done(*ready)
    except CycleError:
        raise ProjectError(422, "Selected members have a dependency cycle") from None
    return [selected[key] for key in order]


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
