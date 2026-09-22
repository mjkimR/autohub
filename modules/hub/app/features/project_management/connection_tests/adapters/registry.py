from app.features.project_management.connection_tests.adapters.base import ConnectionTestAdapter
from app.features.project_management.connection_tests.adapters.codex import CodexConnectionTestAdapter
from app.features.project_management.connection_tests.adapters.jules import JulesConnectionTestAdapter
from app.features.project_management.connection_tests.models import ConnectionTest
from app.features.project_management.projects.errors import ProjectError

ADAPTERS: dict[tuple[str, str], ConnectionTestAdapter] = {
    ("codex", "codex-github-mention"): CodexConnectionTestAdapter(),
    ("jules", "jules-api"): JulesConnectionTestAdapter(),
}


def find_adapter(kind: str, key: str) -> ConnectionTestAdapter | None:
    return ADAPTERS.get((kind, key))


def adapter_for(row: ConnectionTest) -> ConnectionTestAdapter:
    snapshot = row.catalog_snapshot or {"kind": "codex", "adapter": "codex-github-mention"}
    adapter = find_adapter(snapshot["kind"], snapshot["adapter"])
    if adapter is None:
        raise ProjectError(422, "The connection test adapter is unavailable")
    return adapter
