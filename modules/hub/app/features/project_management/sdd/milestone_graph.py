"""Exact catalog-backed dependency observations at one disposable commit checkout."""

from pathlib import Path, PurePosixPath

import yaml
from app.features.project_management.projects.errors import ProjectError

from .services import cli

LIMITS = {"members": 50, "anchors": 200, "edges": 500, "deadline_seconds": 150, "pull_pages": 10}


def safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or str(path) != value:
        raise ProjectError(422, "Use an exact repository-relative document path")
    return value


def metadata(root: Path, path: str) -> dict:
    file = root / safe_path(path)
    if file.resolve() != file.absolute():
        raise ValueError(f"Symlinked anchor: {path}")
    text = file.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError(f"Missing frontmatter: {path}")
    value = yaml.safe_load(text.split("---", 2)[1])
    if not isinstance(value, dict):
        raise ValueError(f"Malformed frontmatter: {path}")
    return value


def is_anchor(row: dict) -> bool:
    path = PurePosixPath(str(row.get("path", "")))
    identity, kind = str(row.get("id", "")), row.get("kind")
    if kind == "proposal":
        return identity.startswith("PROP-") and path.name == "proposal.md" and path.parent.name == identity
    if kind == "spec":
        return identity.startswith("SPEC-") and path.name == "spec.md"
    return kind == "milestone" and identity.startswith("MS-") and path.name == f"{identity}.md"


class MilestoneGraph:
    def __init__(self, root: Path):
        self.root = root
        self.documents: list[dict] = []
        self.reasons: list[str] = []
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.resolutions: dict[str, dict | None] = {}
        self.expanded: set[str] = set()

    async def load(self):
        result = await cli(
            self.root, "docs", "list", "milestone", "proposal", "spec", "--history", "--all-namespaces", "--limit", "0"
        )
        self.documents = result.get("documents", [])
        if result.get("errors") or result.get("notices") or result.get("total") != len(self.documents):
            self.reasons.append("Document catalog coverage is incomplete")
        counts: dict[str, int] = {}
        for row in self.documents:
            counts[row["id"]] = counts.get(row["id"], 0) + 1
        self.reasons.extend(f"Ambiguous document ID: {key}" for key, count in counts.items() if count > 1)

    async def resolve(self, identity: str) -> dict | None:
        if identity not in self.resolutions:
            try:
                result = await cli(self.root, "docs", "resolve", identity)
            except ProjectError as exc:
                self.reasons.append(f"Document resolution unavailable or unresolved: {identity} ({exc.code})")
                self.resolutions[identity] = None
                return None
            rows = result.get("documents", [])
            self.resolutions[identity] = rows[0] if len(rows) == 1 and not result.get("errors") else None
        return self.resolutions[identity]

    async def milestone(self, identity: str, path: str | None) -> dict:
        row = await self.resolve(identity)
        if not row or row.get("kind") != "milestone" or not is_anchor(row) or (path and path != row["path"]):
            raise ProjectError(422, "Milestone ID is missing, ambiguous or does not match its exact path")
        safe_path(row["path"])
        return row

    async def members(self, milestone: dict) -> list[dict]:
        members = []
        for row in self.documents:
            if row.get("kind") != "proposal" or not row.get("path", "").endswith("/proposal.md"):
                continue
            try:
                meta = metadata(self.root, row["path"])
                relation = meta.get("milestone")
                if relation is None:
                    continue
                if not isinstance(relation, str):
                    raise ValueError(f"Malformed milestone relation: {row['path']}")
                resolved = await self.resolve(relation)
                if resolved and resolved.get("id") == milestone["id"]:
                    members.append(row)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                self.reasons.append(f"Unreadable membership anchor {row['path']}: {type(exc).__name__}")
        return sorted(members, key=lambda row: (row["id"], row["path"]))

    async def dependencies(self, row: dict, trail: tuple[str, ...] = ()) -> list[str]:
        identity, path = row["id"], row["path"]
        if identity in trail:
            self.reasons.append(f"Dependency cycle: {identity} ({path})")
            return [f"Dependency cycle: {' -> '.join((*trail, identity))}"]
        try:
            meta = metadata(self.root, path)
            dependencies = meta.get("depends_on", [])
            if not isinstance(dependencies, list) or any(not isinstance(dep, str) for dep in dependencies):
                self.reasons.append(f"Malformed depends_on: {path}")
                return [f"Malformed depends_on: {path}"]
        except (OSError, ValueError, yaml.YAMLError) as exc:
            self.reasons.append(f"Unreadable dependency anchor: {identity} ({path})")
            return [f"Unreadable dependency anchor {identity} ({path}): {type(exc).__name__}"]
        holds = []
        for dependency in dependencies:
            if len(self.edges) >= LIMITS["edges"] + 1:
                return [*holds, "Dependency edge limit exceeded"]
            if dependency not in self.nodes and len(self.nodes) >= LIMITS["anchors"] + 1:
                return [*holds, "Prerequisite anchor limit exceeded"]
            target = await self.resolve(dependency)
            allowed = ("milestone",) if row.get("kind") == "milestone" else ("proposal", "spec")
            edge = {
                "source": identity,
                "requested_id": dependency,
                "canonical_id": None,
                "path": None,
                "status": "unknown",
            }
            self.edges.append(edge)
            if not target or target.get("kind") not in allowed or not is_anchor(target):
                reason = f"Missing, ambiguous or invalid prerequisite {dependency} from {identity} ({path})"
                self.nodes[dependency] = target or {"id": dependency, "status": "unknown", "path": None}
                if target:
                    edge.update(canonical_id=target["id"], path=target["path"], status=target.get("status", "unknown"))
                self.reasons.append(reason)
                holds.append(reason)
                continue
            key = target["id"]
            edge.update(canonical_id=key, path=target["path"], status=target.get("status", "unknown"))
            self.nodes[key] = target
            status = target.get("status")
            satisfied = (target["kind"] == "milestone" and status in ("done", "dropped")) or (
                target["kind"] == "spec" and status == "completed"
            )
            if not satisfied:
                holds.append(f"Prerequisite {dependency} resolves to {key} ({target['path']}) with status {status}")
                if key in (*trail, identity):
                    self.reasons.append(f"Dependency cycle: {identity} -> {key}")
                    holds.append(f"Dependency cycle: {' -> '.join((*trail, identity, key))}")
                elif key not in self.expanded:
                    self.expanded.add(key)
                    holds.extend(await self.dependencies(target, (*trail, identity)))
            # Completed SPEC history is deliberately not traversed.
        return list(dict.fromkeys(holds))
