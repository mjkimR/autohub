from app.mcp.auth import MCPAuthentication, authenticated_context
from app.mcp.connection_tests import register_connection_tests
from app.mcp.dependencies import Dependencies
from app.mcp.projects import register_projects
from app.mcp.runs import register_runs
from app_mcp import ToolRegistry, create_mcp
from starlette.middleware import Middleware


def create_hub_mcp():
    registry = ToolRegistry()
    deps = Dependencies()
    register_projects(registry, deps)
    register_runs(registry, deps)
    register_connection_tests(registry, deps)
    mcp = create_mcp("AutoHub", registry, authenticated_context)
    return mcp.http_app(path="/", stateless_http=True, json_response=True, middleware=[Middleware(MCPAuthentication)])
