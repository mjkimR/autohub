"""Pure selection and drift decisions; no publication or execution collaborators."""

from app.features.project_management.projects.errors import ProjectError

from .milestone_graph import LIMITS, safe_path


def ordered_selection(preview: dict, requested: list[dict]) -> list[dict]:
    if preview.get("milestone", {}).get("status") in ("done", "dropped"):
        raise ProjectError(422, "Finished milestones are inspection only")
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
            or (row["eligibility"] == "held" and row.get("scheduling") != "held")
            or "SDD_BRANCH_EXISTS" in row.get("reasons", [])
            or any((row.get("workflow_hold") or {}).values())
        ):
            raise ProjectError(422, "Selection contains an unsupported or workflow-held member")
        selected[value["id"]] = {**row, "preferences": value}
    graph = {key: set() for key in selected}
    for edge in preview["edges"]:
        if edge["source"] in graph and edge.get("canonical_id") in graph:
            graph[edge["source"]].add(edge["canonical_id"])
    order = []
    remaining = set(graph)
    while remaining:
        next_id = next((key for key in sorted(remaining) if not (graph[key] & remaining)), None)
        if next_id is None:
            raise ProjectError(422, "Selected members have a dependency cycle")
        order.append(next_id)
        remaining.remove(next_id)
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


def graph_drift(original, current, nodes, selected, resolutions=None):
    """Status may advance; identity/adjacency changes need exact canonical repair evidence."""

    def key(edge):
        return (edge["source"], edge["requested_id"], edge.get("canonical_id"), edge.get("path"))

    old, new = {key(e) for e in original}, {key(e) for e in current}
    removed, added = old - new, new - old
    completed = {n["id"] for n in nodes if n.get("kind") == "spec" and n.get("status") == "completed"}
    for edge in list(removed):
        source, requested, canonical, _ = edge
        source_member = selected.get(source)
        if source in completed or (source_member and source_member.state == "succeeded" and source_member.spec_anchor):
            removed.remove(edge)
            continue
        resolved = (resolutions or {}).get(requested)
        if (
            requested.startswith("PROP-")
            and resolved
            and resolved.get("kind") == "spec"
            and resolved.get("status") == "completed"
        ):
            replacement = next(
                (
                    e
                    for e in added
                    if e[0] == source
                    and e[1] in (requested, resolved["id"])
                    and e[2] == resolved["id"]
                    and e[3] == resolved["path"]
                ),
                None,
            )
            if replacement:
                removed.remove(edge)
                added.remove(replacement)
                continue
        predecessor = selected.get(canonical or requested)
        target = (predecessor.spec_anchor or {}).get("id") if predecessor else None
        if not target or predecessor is None or predecessor.state != "succeeded" or not predecessor.outcome:
            continue
        replacement = next(
            (
                e
                for e in added
                if e[0] == source
                and e[1] in (requested, target)
                and e[2] == target
                and e[3] == predecessor.spec_anchor["path"]
            ),
            None,
        )
        if replacement:
            removed.remove(edge)
            added.remove(replacement)
    return "Dependency graph identity changed beyond a proven canonical repair" if removed or added else None
