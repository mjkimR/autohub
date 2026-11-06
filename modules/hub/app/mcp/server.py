from app.auth import MCP_OPS, MCP_WORK_SCOPES
from app.mcp.auth import MCPAuthentication, authenticated_context
from app.mcp.connection_tests import register_connection_tests
from app.mcp.decision_inbox import register_decisions
from app.mcp.dependencies import Dependencies
from app.mcp.interactions import register_interactions
from app.mcp.projects import register_projects
from app.mcp.runs import register_runs
from app.mcp.sdd import register_sdd
from app.mcp.sdd_batches import register_batches
from app.mcp.work_item_recovery import register_recovery
from app.mcp.work_item_replacements import register_replacements
from app.mcp.work_plans import register_work_plans
from app_mcp import ToolRegistry, create_mcp
from starlette.middleware import Middleware


def create_hub_mcp(*, ops: bool = False):
    definitions = ToolRegistry()
    deps = Dependencies()
    register_decisions(definitions, deps)
    register_batches(definitions, deps)
    register_recovery(definitions, deps)
    register_replacements(definitions, deps)
    register_projects(definitions, deps)
    register_runs(definitions, deps)
    register_sdd(definitions, deps)
    register_work_plans(definitions, deps)
    register_interactions(definitions, deps)
    register_connection_tests(definitions, deps)
    registry = ToolRegistry()
    for tool in definitions.definitions():
        # Operations adds tools to the work connection without duplicating discovery.
        if (MCP_OPS in tool.required_scopes) == ops:
            registry.register(tool)
    mcp = create_mcp("AutoHub operations" if ops else "AutoHub", registry, authenticated_context)
    scopes = frozenset({MCP_OPS}) if ops else MCP_WORK_SCOPES
    return mcp.http_app(
        path="/",
        stateless_http=True,
        json_response=True,
        middleware=[Middleware(MCPAuthentication, allowed_scopes=scopes)],
    )
